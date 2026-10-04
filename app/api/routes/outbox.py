from fastapi import APIRouter, Query
from typing import List, Optional
from app.schemas.outbox import (
    QueueEmailRequest, 
    OutboxItem, 
    OutboxStats, 
    OutboxStatus
)
from app.services.outbox_dispatcher import outbox_dispatcher_service

router = APIRouter()

@router.post(
    "/queue",
    response_model=OutboxItem,
    tags=["Outbox & Safeguards"],
    summary="Queue or draft an outreach email",
    description="Adds an approved pitch to the outbox pipeline. In 'draft' mode, creates a safe draft. In 'live_send' mode, checks daily velocity limits."
)
async def queue_email(payload: QueueEmailRequest):
    """
    POST endpoint to queue or draft an outreach message.
    """
    return outbox_dispatcher_service.queue_message(payload)

@router.get(
    "/items",
    response_model=List[OutboxItem],
    tags=["Outbox & Safeguards"],
    summary="List all outbox messages",
    description="Returns all tracked messages in the outreach pipeline, optionally filtered by status."
)
async def list_outbox_items(
    status: Optional[OutboxStatus] = Query(default=None, description="Optional status filter: draft, sent, queued, etc.")
):
    """
    GET endpoint to retrieve pipeline items.
    """
    return outbox_dispatcher_service.list_items(status=status)

@router.get(
    "/stats",
    response_model=OutboxStats,
    tags=["Outbox & Safeguards"],
    summary="Get sending quota & pipeline stats",
    description="Returns current daily limits, emails sent today, remaining quota, and total counts."
)
async def get_outbox_stats():
    """
    GET endpoint to check delivery limits and safety quotas.
    """
    return outbox_dispatcher_service.get_stats()
