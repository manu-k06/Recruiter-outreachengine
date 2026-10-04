from fastapi import APIRouter
from app.schemas.resume import ParseResumeRequest, ParsedResume
from app.services.resume_parser import resume_parser_service

router = APIRouter()

@router.post(
    "/parse-markdown",
    response_model=ParsedResume,
    tags=["Resume & Profile"],
    summary="Parse a Markdown (.md) resume",
    description="Extracts candidate name, core technical skills, featured projects, links, and background directly from Markdown text."
)
async def parse_markdown_resume(payload: ParseResumeRequest):
    return resume_parser_service.parse_markdown(payload.markdown_content)
