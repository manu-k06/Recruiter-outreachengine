from pydantic import BaseModel, Field
from typing import List, Optional

class ReviewPitchRequest(BaseModel):
    """
    Input for AI pitch review and diagnostic rating.
    """
    subject_line: str = Field(..., description="The cold email subject line")
    body: str = Field(..., description="The cold email body to review")
    company_name: str = Field(..., description="Target company")
    recruiter_name: str = Field(..., description="Target recruiter")
    custom_guidelines: Optional[List[str]] = Field(
        default_factory=lambda: [
            "Keep total length under 90 words",
            "Must have a clear, low-friction closing question",
            "Must mention at least 2 relevant technical skills",
            "Avoid generic buzzwords like 'rockstar' or 'hard worker'"
        ],
        description="List of quality rules to check against"
    )

class ReviewPitchResponse(BaseModel):
    """
    AI review verdict, diagnostic scores, and actionable improvements.
    """
    overall_score: int = Field(..., ge=0, le=100, description="Overall readiness score (0-100)")
    brevity_score: int = Field(..., ge=0, le=100, description="Score based on word count & scanability")
    relevance_score: int = Field(..., ge=0, le=100, description="Score based on company/role personalization")
    cta_score: int = Field(..., ge=0, le=100, description="Score based on how easy the closing question is to answer")
    word_count: int
    readiness: str = Field(..., description="'Ready to Send', 'Minor Edits Recommended', or 'Needs Revision'")
    strengths: List[str] = Field(default_factory=list)
    actionable_improvements: List[str] = Field(default_factory=list)

class RefinePitchRequest(BaseModel):
    """
    Input to rewrite/refine an email using natural language instructions.
    """
    current_subject: str
    current_body: str
    instruction: str = Field(
        ..., 
        description="How to refine it, e.g. 'Make it shorter and punchier', 'Focus more on Cineforge and AI'",
        examples=["Make it under 60 words and highlight Cineforge"]
    )
    company_name: str
    recruiter_name: str

class RefinePitchResponse(BaseModel):
    """
    The refined and polished cold email.
    """
    refined_subject: str
    refined_body: str
    word_count: int
    changes_summary: str
