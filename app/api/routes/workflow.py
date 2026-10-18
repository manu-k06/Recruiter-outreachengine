from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_store
from app.core.storage import SQLiteStore, RecordConflictError, RecordNotFoundError
from app.schemas.outbox import OutboxItem, OutboxStatus
from app.schemas.pitch import GeneratePitchRequest, GeneratedPitchResponse
from app.schemas.recruiter import DiscoverRecruitersRequest, DiscoverRecruitersResponse, RecruiterLead
from app.schemas.storage import SavedDiscovery
from app.schemas.workflow import PitchFromRecords, SaveWorkflowDraft, ManualContact, EditDraft
from app.services.pitch_generator import pitch_generator_service

router = APIRouter(tags=["Draft workflow"])


def resolve_records(payload: PitchFromRecords, store: SQLiteStore):
    profile = store.get_profile(str(payload.profile_id))
    discovery = store.get_discovery(str(payload.discovery_id))
    if profile is None or discovery is None:
        raise HTTPException(status_code=404, detail="Saved profile or discovery not found")
    if payload.lead_index >= len(discovery.result.leads):
        raise HTTPException(status_code=404, detail="Lead not found in this discovery")
    return profile, discovery.result.leads[payload.lead_index]


@router.post("/workflow/preview", response_model=GeneratedPitchResponse)
def preview(payload: PitchFromRecords, store: SQLiteStore = Depends(get_store)):
    profile, lead = resolve_records(payload, store)
    return pitch_generator_service.generate_pitch(GeneratePitchRequest(
        candidate=profile.candidate, recruiter_name=lead.full_name,
        recruiter_title=lead.job_title, company_name=lead.company, tone=payload.tone,
    ))


@router.post("/workflow/drafts", response_model=OutboxItem)
def save_draft(payload: SaveWorkflowDraft, store: SQLiteStore = Depends(get_store)):
    profile, lead = resolve_records(payload, store)
    item = OutboxItem(
        id=str(payload.request_id), created_at=datetime.now(timezone.utc),
        recipient_email=str(payload.recipient_email), recipient_name=lead.full_name,
        company_name=lead.company, subject_line=payload.subject_line, body=payload.body,
        status=OutboxStatus.DRAFT, profile_id=profile.id, discovery_id=str(payload.discovery_id),
        lead_index=payload.lead_index, note="Draft saved after recipient review. No email was sent.",
    )
    try:
        return store.save_workflow_draft(item)
    except RecordConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/outbox/items/{item_id}", response_model=OutboxItem)
def edit_draft(item_id: str, payload: EditDraft, store: SQLiteStore = Depends(get_store)):
    try:
        return store.edit_draft(item_id, payload)
    except RecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RecordConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/workflow/contacts", response_model=SavedDiscovery, status_code=201)
def add_contact(payload: ManualContact, store: SQLiteStore = Depends(get_store)):
    parts = payload.full_name.split(maxsplit=1)
    lead = RecruiterLead(
        full_name=payload.full_name, first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
        job_title=payload.job_title, company=payload.company, company_domain=payload.company_domain,
        profile_url=str(payload.source_url) if payload.source_url else None,
        candidate_emails=[str(payload.email)] if payload.email else [], status="unverified",
    )
    request = DiscoverRecruitersRequest(company=payload.company, company_domain=payload.company_domain, role_keyword=payload.job_title, max_results=1)
    result = DiscoverRecruitersResponse(
        company=payload.company, company_domain=payload.company_domain, total_found=1, leads=[lead],
        warnings=["Manually entered contact. Employment and email ownership have not been verified."],
    )
    return store.save_discovery(request, result)
