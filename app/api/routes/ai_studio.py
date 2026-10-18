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
    summary="Review a cold outreach email using basic rules",
    description="Provides heuristic writing feedback. Custom guidelines and factual claims need manual review; this is not approval to send."
)
async def review_pitch(payload: ReviewPitchRequest):
    return ai_reviewer_service.review_pitch(payload)

@router.post(
    "/refine",
    response_model=RefinePitchResponse,
    tags=["AI Studio & Reviewer"],
    summary="Refine or rewrite an email with custom instructions",
    description="Shortens supported filler phrases while preserving candidate facts. Unsupported instructions are reported for manual editing. No AI model is called."
)
async def refine_pitch(payload: RefinePitchRequest):
    return ai_reviewer_service.refine_pitch(payload)
