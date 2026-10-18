from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from app.schemas.inputs import ShortText, BodyText

class CandidateProfile(BaseModel):
    """
    Candidate Background & Skills Model.
    Represents the job seeker's information used to craft the personalized pitch.
    """
    candidate_name: ShortText = Field(
        ..., 
        description="Your name as it should appear in the email sign-off",
        examples=["Manu K"]
    )
    target_role: ShortText = Field(
        ...,
        description="The role you are applying or pitching for",
        examples=["Full-Stack Engineer", "Backend Developer", "AI Engineer"]
    )
    core_skills: List[ShortText] = Field(
        default_factory=list, max_length=50,
        description="Key technologies or strengths you want highlighted"
    )
    featured_project: Optional[BodyText] = Field(
        default=None,
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
    recruiter_name: ShortText = Field(..., description="Recruiter's full or first name", examples=["Sarah Jenkins"])
    recruiter_title: ShortText = Field(..., description="Recruiter's job title", examples=["Lead Technical Recruiter"])
    company_name: ShortText = Field(..., description="Target company name", examples=["Stripe"])
    candidate: CandidateProfile
    tone: Literal["direct", "technical", "conversational"] = Field(
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
    word_count: int = Field(..., description="Measured word count; no length guarantee")
    matched_skills: List[str] = Field(default_factory=list, description="Skills highlighted in this pitch")
    call_to_action: str = Field(..., description="The low-friction closing ask")
