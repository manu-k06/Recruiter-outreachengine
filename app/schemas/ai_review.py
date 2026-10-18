from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.inputs import ShortText, BodyText

class ReviewPitchRequest(BaseModel):
    """
    Input for AI pitch review and diagnostic rating.
    """
    subject_line: ShortText = Field(..., description="The cold email subject line")
    body: BodyText = Field(..., description="The cold email body to review")
    company_name: ShortText = Field(..., description="Target company")
    recruiter_name: ShortText = Field(..., description="Target recruiter")
    custom_guidelines: Optional[List[ShortText]] = Field(
        default_factory=lambda: [
            "Keep total length under 90 words",
            "Must have a clear, low-friction closing question",
            "Must mention at least 2 relevant technical skills",
            "Avoid generic buzzwords like 'rockstar' or 'hard worker'"
        ],
        max_length=30, description="Guidelines retained for manual review; not evaluated by the heuristic"
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
    readiness: str = Field(..., description="Heuristic feedback only; never approval to send")
    strengths: List[str] = Field(default_factory=list)
    actionable_improvements: List[str] = Field(default_factory=list)
    review_method: str = "heuristic"
    unchecked_guidelines: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class RefinePitchRequest(BaseModel):
    """
    Input to rewrite/refine an email using natural language instructions.
    """
    current_subject: ShortText
    current_body: BodyText
    instruction: ShortText = Field(
        ..., 
        description="How to refine it, e.g. 'Make it shorter and punchier', 'Focus more on Cineforge and AI'",
        examples=["Make it under 60 words and highlight Cineforge"]
    )
    company_name: ShortText
    recruiter_name: ShortText

class RefinePitchResponse(BaseModel):
    """
    The refined and polished cold email.
    """
    refined_subject: str
    refined_body: str
    word_count: int
    changes_summary: str
    refinement_method: str = "conservative_rules"
    warnings: List[str] = Field(default_factory=list)
