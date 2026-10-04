from fastapi import APIRouter
from app.schemas.pitch import GeneratePitchRequest, GeneratedPitchResponse
from app.services.pitch_generator import pitch_generator_service

router = APIRouter()

@router.post(
    "/generate-pitch",
    response_model=GeneratedPitchResponse,
    tags=["Pitch Generation"],
    summary="Generate a tailored cold outreach pitch",
    description="Generates an ultra-concise, high-converting cold email tailored to the recruiter, company, and candidate profile."
)
async def generate_pitch(payload: GeneratePitchRequest):
    """
    POST endpoint for pitch generation.
    """
    result = pitch_generator_service.generate_pitch(payload)
    return result
