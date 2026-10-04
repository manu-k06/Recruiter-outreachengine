import asyncio
import re
import socket
from typing import List, Tuple, Optional
import dns.asyncresolver
import dns.resolver

from app.schemas.verifier import VerifyEmailResponse, EmailStatus

# Set of commonly known throwaway / burner email domains
# We block these immediately because no legitimate recruiter uses a burner inbox
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", 
    "tempmail.com", "yopmail.com", "trashmail.com", "sharklasers.com",
    "getairmail.com", "dispostable.com", "throwawaymail.com"
}

# Standard email syntax pattern (RFC 5322 compliant regex)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

class EmailVerifierService:
    """
    Core Deliverability Service.
    Performs multi-stage non-intrusive email verification without sending an email.
    """

    def __init__(self, dns_timeout: float = 3.0, smtp_timeout: float = 4.0):
        self.dns_timeout = dns_timeout
        self.smtp_timeout = smtp_timeout
        self.resolver = dns.asyncresolver.Resolver()
        self.resolver.lifetime = self.dns_timeout

    def check_syntax(self, email: str) -> bool:
        """
        Check 1: Syntax Format
        Verifies the email has a valid username, single '@', valid domain, and extension.
        """
        if not email or len(email) > 254:
            return False
        return bool(EMAIL_REGEX.match(email.strip()))

    def check_disposable(self, domain: str) -> bool:
        """
        Check 2: Disposable Domain Filter
        Returns True if the domain is on our burner blacklist.
        """
        return domain.lower() in DISPOSABLE_DOMAINS

    async def get_mx_records(self, domain: str) -> List[str]:
        """
        Check 3: DNS MX (Mail Exchange) Lookup
        Asks the global DNS phonebook: 'Who handles incoming emails for this domain?'
        Returns a list of mail server hostnames sorted by priority (lowest number first).
        """
        try:
            answers = await self.resolver.resolve(domain, "MX")
            # Sort servers by their priority preference (e.g. preference 10 comes before 20)
            sorted_records = sorted(answers, key=lambda record: record.preference)
            return [str(r.exchange).rstrip(".") for r in sorted_records]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.LifetimeTimeout, Exception):
            return []

    async def ping_smtp_mailbox(self, mx_host: str, email: str) -> Tuple[bool, Optional[bool], str]:
        """
        Check 4: SMTP Handshake Simulation
        Knocks on the mail server door, asks if the specific mailbox exists, 
        and disconnects cleanly with 'QUIT' before sending any message body.
        
        Returns:
            (connected: bool, mailbox_exists: bool or None, diagnostic_msg: str)
        """
        reader = None
        writer = None
        try:
            # Step A: Connect to Mail Server on Port 25 (Standard Mail Port)
            connection = asyncio.open_connection(mx_host, 25)
            reader, writer = await asyncio.wait_for(connection, timeout=self.smtp_timeout)

            # Step B: Read initial greeting from server (Expects code 220)
            banner = await asyncio.wait_for(reader.readline(), timeout=self.smtp_timeout)
            if not banner.startswith(b"220"):
                return True, None, "Server did not provide standard 220 greeting."

            # Step C: Say HELO (Introduce our verification engine)
            writer.write(b"HELO outreach-verifier.local\r\n")
            await writer.drain()
            helo_response = await asyncio.wait_for(reader.readline(), timeout=self.smtp_timeout)

            # Step D: MAIL FROM (Simulate a sender address)
            writer.write(b"MAIL FROM:<verify@outreach-verifier.local>\r\n")
            await writer.drain()
            from_response = await asyncio.wait_for(reader.readline(), timeout=self.smtp_timeout)

            # Step E: RCPT TO (Ask if the recruiter's email exists!)
            writer.write(f"RCPT TO:<{email}>\r\n".encode("utf-8"))
            await writer.drain()
            rcpt_response = await asyncio.wait_for(reader.readline(), timeout=self.smtp_timeout)

            # Clean exit
            writer.write(b"QUIT\r\n")
            await writer.drain()

            code = rcpt_response[:3]
            # 250 means: "Recipient OK. Mailbox exists and will receive mail."
            if code == b"250":
                return True, True, "Mailbox confirmed active and accepting mail (250 OK)."
            # 550 / 551 / 553 means: "User does not exist"
            elif code in (b"550", b"551", b"553"):
                return True, False, f"Mailbox rejected by server: {rcpt_response.decode('utf-8', errors='ignore').strip()}"
            else:
                return True, None, f"Server responded with unconfirmed code: {rcpt_response.decode('utf-8', errors='ignore').strip()}"

        except (asyncio.TimeoutError, ConnectionRefusedError, socket.error, OSError) as e:
            # In many home/office internet connections, ISPs block port 25 to prevent residential spam.
            # When blocked, we gracefully report that direct SMTP ping was unreachable.
            return False, None, f"SMTP Port 25 unreachable or blocked by network: {type(e).__name__}"
        finally:
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

    async def verify(self, email: str) -> VerifyEmailResponse:
        """
        Executes the full pipeline sequentially and computes the overall deliverability score.
        """
        clean_email = email.strip().lower()

        # Step 1: Format / Syntax check
        if not self.check_syntax(clean_email):
            return VerifyEmailResponse(
                email=clean_email,
                is_valid_syntax=False,
                is_disposable=False,
                has_mx_records=False,
                mx_servers=[],
                smtp_connected=False,
                mailbox_exists=False,
                deliverability_score=0,
                status=EmailStatus.INVALID,
                diagnostic_reason="Invalid email format syntax."
            )

        # Extract domain
        domain = clean_email.split("@")[1]

        # Step 2: Disposable Domain check
        if self.check_disposable(domain):
            return VerifyEmailResponse(
                email=clean_email,
                is_valid_syntax=True,
                is_disposable=True,
                has_mx_records=False,
                mx_servers=[],
                smtp_connected=False,
                mailbox_exists=False,
                deliverability_score=0,
                status=EmailStatus.INVALID,
                diagnostic_reason="Disposable burner email detected. Will not reach a recruiter."
            )

        # Step 3: DNS MX Records check
        mx_servers = await self.get_mx_records(domain)
        if not mx_servers:
            return VerifyEmailResponse(
                email=clean_email,
                is_valid_syntax=True,
                is_disposable=False,
                has_mx_records=False,
                mx_servers=[],
                smtp_connected=False,
                mailbox_exists=False,
                deliverability_score=0,
                status=EmailStatus.INVALID,
                diagnostic_reason=f"Domain '{domain}' has no active mail servers (No MX records found)."
            )

        # Step 4: SMTP Handshake check against the primary MX server
        primary_mx = mx_servers[0]
        connected, exists, msg = await self.ping_smtp_mailbox(primary_mx, clean_email)

        # Calculate final verdict and score
        if exists is True:
            score = 98
            status = EmailStatus.VALID
            reason = "Email verified! Mailbox exists on host server."
        elif exists is False:
            score = 5
            status = EmailStatus.INVALID
            reason = f"Mailbox definitely does not exist: {msg}"
        else:
            # Mailbox ping was inconclusive (e.g. ISP blocked port 25 or server catch-all)
            # But syntax and MX records are 100% genuine!
            score = 75
            status = EmailStatus.RISKY
            reason = f"Domain has valid MX servers ({primary_mx}), but live ping was inconclusive: {msg}"

        return VerifyEmailResponse(
            email=clean_email,
            is_valid_syntax=True,
            is_disposable=False,
            has_mx_records=True,
            mx_servers=mx_servers,
            smtp_connected=connected,
            mailbox_exists=exists,
            deliverability_score=score,
            status=status,
            diagnostic_reason=reason
        )

# Singleton instance
email_verifier_service = EmailVerifierService()
