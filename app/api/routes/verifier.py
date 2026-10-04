from fastapi import APIRouter, Query, HTTPException, status
from app.schemas.verifier import VerifyEmailRequest, VerifyEmailResponse
from app.services.email_verifier import email_verifier_service

router = APIRouter()

@router.post(
    "/verify-email", 
    response_model=VerifyEmailResponse, 
    tags=["Deliverability"],
    summary="Verify an email address",
    description="Validates email syntax, checks for disposable domains, queries DNS MX records, and simulates an SMTP mailbox ping."
)
async def verify_email_post(payload: VerifyEmailRequest):
    """
    POST endpoint for verifying an email payload.
    Used by frontend dashboards submitting JSON forms.
    """
    result = await email_verifier_service.verify(payload.email)
    return result

@router.get(
    "/verify-email", 
    response_model=VerifyEmailResponse, 
    tags=["Deliverability"],
    summary="Quick-verify email via query parameter",
    description="Allows quick verification via browser URL, e.g.: /api/v1/verify-email?email=test@stripe.com"
)
async def verify_email_get(
    email: str = Query(..., description="The email address to verify", examples=["recruiter@stripe.com"])
):
    """
    GET endpoint for quick testing via URL query parameters.
    """
    result = await email_verifier_service.verify(email)
    return result
