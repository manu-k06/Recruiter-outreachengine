from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from enum import Enum

class EmailStatus(str, Enum):
    """
    Enum represents a fixed set of allowed choices.
    This prevents typos: the status can ONLY be one of these three words.
    """
    VALID = "valid"        # Safe to send! High confidence.
    RISKY = "risky"        # Might be a catch-all server or restricted.
    INVALID = "invalid"    # Do not send! Will bounce and hurt your domain.

class VerifyEmailRequest(BaseModel):
    """
    The input form: what the user/frontend sends to our API.
    """
    email: str = Field(
        ..., 
        description="The candidate email address to verify",
        examples=["recruiter@stripe.com"]
    )

class VerifyEmailResponse(BaseModel):
    """
    The output form: what our API sends back with all diagnostic details.
    """
    email: str
    is_valid_syntax: bool = Field(
        ..., 
        description="True if the string complies with international email standards (RFC 5322)."
    )
    is_disposable: bool = Field(
        ..., 
        description="True if the domain is a temporary/throwaway email service (e.g., Mailinator)."
    )
    has_mx_records: bool = Field(
        ..., 
        description="True if the domain has configured mail servers ready to receive mail."
    )
    mx_servers: List[str] = Field(
        default_factory=list, 
        description="List of mail exchanger server hostnames found in DNS."
    )
    smtp_connected: bool = Field(
        ..., 
        description="True if our engine successfully connected to their mail server."
    )
    mailbox_exists: Optional[bool] = Field(
        default=None, 
        description="True if their server acknowledged the specific mailbox exists."
    )
    deliverability_score: int = Field(
        ..., 
        ge=0, 
        le=100, 
        description="Deliverability score from 0 (guaranteed bounce) to 100 (safe)."
    )
    status: EmailStatus = Field(
        ..., 
        description="Final verdict: valid, risky, or invalid."
    )
    diagnostic_reason: str = Field(
        ..., 
        description="Human-readable explanation of why this verdict was given."
    )
