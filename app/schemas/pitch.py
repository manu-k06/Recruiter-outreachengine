from pydantic import BaseModel, Field
from typing import List, Optional

class CandidateProfile(BaseModel):
    """
    Candidate Background & Skills Model.
    Represents the job seeker's information used to craft the personalized pitch.
    """
    candidate_name: str = Field(
        ..., 
        description="Your name as it should appear in the email sign-off",
        examples=["Manu K"]
    )
    target_role: str = Field(
        default="Full-Stack / Python Engineer", 
        description="The role you are applying or pitching for",
        examples=["Full-Stack Engineer", "Backend Developer", "AI Engineer"]
    )
    core_skills: List[str] = Field(
        default_factory=lambda: ["Python", "FastAPI", "React", "Supabase", "AI/LLM Integration"],
        description="Key technologies or strengths you want highlighted"
    )
    featured_project: Optional[str] = Field(
        default="Cineforge (AI-driven discovery platform built with FastAPI, React, and Supabase)",
        description="Notable project or achievement you want mentioned"
    )
    portfolio_url: Optional[str] = Field(
        default=None,
        description="Link to your portfolio or GitHub (e.g. https://github.com/manu-k06)",
        examples=["https://github.com/manu-k06"]
    )

class GeneratePitchRequest(BaseModel):
    """
    Input payload for generating a tailored outreach pitch.
    """
    recruiter_name: str = Field(..., description="Recruiter's full or first name", examples=["Sarah Jenkins"])
    recruiter_title: str = Field(..., description="Recruiter's job title", examples=["Lead Technical Recruiter"])
    company_name: str = Field(..., description="Target company name", examples=["Stripe"])
    candidate: CandidateProfile = Field(default_factory=CandidateProfile)
    tone: str = Field(
        default="direct", 
        description="Tone of the email: 'direct' (concise, 3 bullets), 'technical' (engineering-focused), or 'conversational'",
        examples=["direct", "technical", "conversational"]
    )

class GeneratedPitchResponse(BaseModel):
    """
    The generated email package ready to be reviewed or sent.
    """
    recipient_email: Optional[str] = None
    recipient_name: str
    company_name: str
    subject_line: str = Field(..., description="High-converting email subject line")
    body: str = Field(..., description="Formatted email message body")
    word_count: int = Field(..., description="Total word count (kept under 120 words for high read rates)")
    matched_skills: List[str] = Field(default_factory=list, description="Skills highlighted in this pitch")
    call_to_action: str = Field(..., description="The low-friction closing ask")
