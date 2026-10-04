from fastapi import APIRouter
from app.schemas.ai_review import (
    ReviewPitchRequest, 
    ReviewPitchResponse, 
    RefinePitchRequest, 
    RefinePitchResponse
)
from app.services.ai_reviewer import ai_reviewer_service

router = APIRouter()

@router.post(
    "/review",
    response_model=ReviewPitchResponse,
    tags=["AI Studio & Reviewer"],
    summary="Review and score a cold outreach email",
    description="Scores pitch on Brevity, Personalization, and Call-to-Action. Provides actionable advice to maximize response rates."
)
async def review_pitch(payload: ReviewPitchRequest):
    return ai_reviewer_service.review_pitch(payload)

@router.post(
    "/refine",
    response_model=RefinePitchResponse,
    tags=["AI Studio & Reviewer"],
    summary="Refine or rewrite an email with custom instructions",
    description="Applies prompt instructions (e.g. 'Make it punchier', 'Highlight Cineforge') to polish the cold email."
)
async def refine_pitch(payload: RefinePitchRequest):
    return ai_reviewer_service.refine_pitch(payload)
