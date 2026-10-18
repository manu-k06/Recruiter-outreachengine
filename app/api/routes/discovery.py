from fastapi import APIRouter, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from typing import Optional
from app.schemas.recruiter import DiscoverRecruitersRequest, DiscoverRecruitersResponse
from app.services.recruiter_discovery import recruiter_discovery_service

router = APIRouter()

@router.post(
    "/discover-recruiters",
    response_model=DiscoverRecruitersResponse,
    tags=["Discovery"],
    summary="Discover recruiters for a target company",
    description="Discovers recruiter contacts, parses names/titles, generates corporate email patterns, and verifies deliverability."
)
async def discover_recruiters_post(payload: DiscoverRecruitersRequest):
    """
    POST endpoint for recruiter discovery.
    """
    result = await recruiter_discovery_service.discover(
        company=payload.company,
        role_keyword=payload.role_keyword,
        custom_domain=payload.company_domain,
        max_results=payload.max_results
    )
    return result

@router.get(
    "/discover-recruiters",
    response_model=DiscoverRecruitersResponse,
    tags=["Discovery"],
    summary="Quick-discover recruiters via query parameter",
    description="Example: /api/v1/discover-recruiters?company=Stripe&role=Technical%20Recruiter"
)
async def discover_recruiters_get(
    company: str = Query(..., max_length=200, description="Target company name, e.g. Stripe"),
    role: str = Query(default="Technical Recruiter", max_length=200, description="Role to target"),
    domain: Optional[str] = Query(default=None, max_length=253, description="Optional custom domain, e.g. stripe.com"),
    max_results: int = Query(default=3, ge=1, le=10)
):
    """
    GET endpoint for rapid testing via browser URL.
    """
    # Reuse the POST model so both routes apply identical trimming and validation.
    try:
        payload = DiscoverRecruitersRequest(company=company, role_keyword=role, company_domain=domain, max_results=max_results)
    except ValidationError as exc:
        names = {"role_keyword": "role", "company_domain": "domain"}
        errors = [{**error, "loc": ("query", names.get(error["loc"][0], error["loc"][0]), *error["loc"][1:])} for error in exc.errors()]
        raise RequestValidationError(errors) from exc
    return await discover_recruiters_post(payload)
