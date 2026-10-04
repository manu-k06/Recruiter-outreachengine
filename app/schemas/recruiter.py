from pydantic import BaseModel, Field
from typing import List, Optional

class DiscoverRecruitersRequest(BaseModel):
    """
    Search input form: what the user requests from the discovery engine.
    """
    company: str = Field(
        ..., 
        description="Target company name", 
        examples=["Stripe", "Datadog", "Vercel"]
    )
    role_keyword: str = Field(
        default="Technical Recruiter", 
        description="Recruiter role or title to target (e.g. 'Technical Recruiter', 'Head of Talent')",
        examples=["Technical Recruiter", "Talent Acquisition"]
    )
    company_domain: Optional[str] = Field(
        default=None, 
        description="Optional custom domain (e.g. stripe.com). If omitted, the engine infers it.",
        examples=["stripe.com"]
    )
    max_results: int = Field(
        default=5, 
        ge=1, 
        le=15, 
        description="Maximum number of recruiter leads to discover in one batch."
    )

class RecruiterLead(BaseModel):
    """
    A single discovered recruiter contact and verified outreach target.
    """
    full_name: str = Field(..., description="Recruiter's full name, e.g. 'Sarah Jenkins'")
    first_name: str
    last_name: str
    job_title: str = Field(..., description="Discovered title, e.g. 'Senior Technical Recruiter'")
    company: str = Field(..., description="Target company name, e.g. 'Stripe'")
    company_domain: str = Field(..., description="Domain used for email generation, e.g. 'stripe.com'")
    profile_url: Optional[str] = Field(default=None, description="Public profile link (if discovered)")
    
    # Email generation & verification diagnostics
    candidate_emails: List[str] = Field(
        default_factory=list, 
        description="Generated email variations tested (e.g. first.last@company.com)"
    )
    recommended_email: Optional[str] = Field(
        default=None, 
        description="The highest-confidence verified email address for this person."
    )
    deliverability_score: int = Field(
        default=0, 
        ge=0, 
        le=100, 
        description="Confidence score (0-100) from our Module 2 deliverability engine."
    )
    status: str = Field(
        default="unverified", 
        description="Deliverability status: 'valid', 'risky', or 'unverified'"
    )

class DiscoverRecruitersResponse(BaseModel):
    """
    The collection of discovered leads returned to the user or dashboard.
    """
    company: str
    company_domain: str
    total_found: int
    leads: List[RecruiterLead] = Field(default_factory=list)
