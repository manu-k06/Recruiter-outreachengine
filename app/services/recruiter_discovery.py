import re
import urllib.parse
from typing import List, Tuple, Optional
import httpx

from app.schemas.recruiter import RecruiterLead, DiscoverRecruitersResponse
from app.services.email_verifier import email_verifier_service

class RecruiterDiscoveryService:
    """
    Recruiter Lead Discovery Service.
    Finds recruiters without risking LinkedIn account bans by using public search queries,
    extracts names, generates corporate email patterns, and verifies deliverability.
    """

    def infer_domain(self, company: str, custom_domain: Optional[str] = None) -> str:
        """
        Infers the primary domain name from a company name if not provided.
        Example: 'Stripe' -> 'stripe.com', 'DataDog' -> 'datadoghq.com'
        """
        if custom_domain:
            return custom_domain.strip().lower()
            
        clean = re.sub(r"[^a-zA-Z0-9]", "", company).lower()
        if clean == "datadog":
            return "datadoghq.com"
        return f"{clean}.com"

    def split_name(self, full_name: str) -> Tuple[str, str]:
        """
        Splits a full name into (first_name, last_name).
        Example: 'Sarah Jenkins' -> ('Sarah', 'Jenkins')
        """
        parts = full_name.strip().split()
        if not parts:
            return "", ""
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    def generate_email_patterns(self, first: str, last: str, domain: str) -> List[str]:
        """
        Generates standard corporate email variations for a person.
        Example for ('Sarah', 'Jenkins', 'stripe.com'):
          1. sarah.jenkins@stripe.com   (first.last - 60% of tech firms)
          2. sarah@stripe.com           (first - 25% of startups)
          3. sjenkins@stripe.com        (flast - 15% of enterprises)
        """
        f = re.sub(r"[^a-zA-Z0-9]", "", first).lower()
        l = re.sub(r"[^a-zA-Z0-9]", "", last).lower()
        d = domain.lower()

        patterns = []
        if f and l:
            patterns.append(f"{f}.{l}@{d}")
            patterns.append(f"{f}@{d}")
            patterns.append(f"{f[0]}{l}@{d}")
            patterns.append(f"{f}_{l}@{d}")
        elif f:
            patterns.append(f"{f}@{d}")

        return patterns

    def parse_search_snippet(self, raw_text: str, target_company: str) -> Optional[Tuple[str, str]]:
        """
        Parses a public search result title/snippet.
        Typical format: 'Sarah Jenkins - Senior Technical Recruiter - Stripe | LinkedIn'
        Extracts: Name and Job Title
        """
        # Remove trailing '| LinkedIn'
        cleaned = re.sub(r"\|.*$", "", raw_text).strip()
        parts = [p.strip() for p in cleaned.split(" - ") if p.strip()]
        
        if len(parts) >= 2:
            name = parts[0]
            title = parts[1]
            # Sanity checks
            if len(name.split()) >= 2 and len(name) < 40:
                return name, title
        return None

    async def search_public_profiles(self, company: str, role_keyword: str, max_results: int) -> List[Tuple[str, str]]:
        """
        Queries public search engines for indexed LinkedIn recruiter profiles.
        Query format: site:linkedin.com/in "Technical Recruiter" "Stripe"
        """
        query = f'site:linkedin.com/in "{role_keyword}" "{company}"'
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        extracted_profiles: List[Tuple[str, str]] = []

        try:
            async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    # Parse link titles from HTML
                    matches = re.findall(r'<a class="result__url"[^>]*>(.*?)</a>', res.text)
                    snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', res.text)
                    
                    # Also look for title matches in <a> tags
                    title_matches = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', res.text)
                    # Simple regex extraction of 'First Last - Title - Company'
                    raw_lines = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)\s*-\s*([^-\n<]+)\s*-\s*' + re.escape(company), res.text, re.IGNORECASE)
                    for match in raw_lines:
                        name, title = match
                        extracted_profiles.append((name.strip(), title.strip()))
                        if len(extracted_profiles) >= max_results:
                            break
        except httpx.HTTPError:
            # Unavailable search stays empty; never replace it with sample people.
            return []

        return extracted_profiles

    async def discover(
        self, 
        company: str, 
        role_keyword: str = "Technical Recruiter", 
        custom_domain: Optional[str] = None, 
        max_results: int = 5
    ) -> DiscoverRecruitersResponse:
        """
        Main pipeline:
        1. Injects/infers domain
        2. Discovers recruiter candidates from live search only
        3. Generates corporate email patterns
        4. Verifies deliverability with Module 2 engine
        """
        domain = self.infer_domain(company, custom_domain)
        warnings = ["Search snippets do not confirm current employment or address ownership. Email patterns are guesses, not recommendations."]
        if not custom_domain:
            warnings.append("Company domain is inferred and must be confirmed before outreach.")

        # Step A: Discover Raw Names & Titles
        raw_candidates = await self.search_public_profiles(company, role_keyword, max_results)

        # An empty or unavailable search is a real result, not a reason to invent people.
        if not raw_candidates:
            warnings.append("No recruiter profiles were extracted. Search may be unavailable or have no matching results.")

        # Step B: Process each recruiter lead
        leads: List[RecruiterLead] = []

        for full_name, title in raw_candidates[:max_results]:
            first, last = self.split_name(full_name)
            candidate_emails = self.generate_email_patterns(first, last, domain)
            
            probe_email = candidate_emails[0] if candidate_emails else None

            # Verify the recommended email through our Module 2 Deliverability Engine!
            deliverability_score = 0
            status_str = "unverified"
            if probe_email:
                verification = await email_verifier_service.verify(probe_email)
                deliverability_score = verification.deliverability_score
                status_str = verification.status.value

            lead = RecruiterLead(
                full_name=full_name,
                first_name=first,
                last_name=last,
                job_title=title,
                company=company,
                company_domain=domain,
                candidate_emails=candidate_emails,
                recommended_email=None,
                deliverability_score=deliverability_score,
                status=status_str
            )
            leads.append(lead)

        return DiscoverRecruitersResponse(
            company=company,
            company_domain=domain,
            total_found=len(leads),
            leads=leads,
            warnings=warnings,
        )

# Singleton instance
recruiter_discovery_service = RecruiterDiscoveryService()
