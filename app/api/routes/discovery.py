from fastapi import APIRouter, Query
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
    company: str = Query(..., description="Target company name, e.g. Stripe"),
    role: str = Query(default="Technical Recruiter", description="Role to target"),
    domain: Optional[str] = Query(default=None, description="Optional custom domain, e.g. stripe.com"),
    max_results: int = Query(default=3, ge=1, le=10)
):
    """
    GET endpoint for rapid testing via browser URL.
    """
    result = await recruiter_discovery_service.discover(
        company=company,
        role_keyword=role,
        custom_domain=domain,
        max_results=max_results
    )
    return result
