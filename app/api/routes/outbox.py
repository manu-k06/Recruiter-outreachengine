from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from app.schemas.outbox import (
    QueueEmailRequest, 
    OutboxItem, 
    OutboxStats, 
    OutboxStatus
)
from app.services.outbox_dispatcher import OutboxDispatcherService, LiveSendingUnavailableError
from app.api.dependencies import get_outbox

router = APIRouter()

@router.post(
    "/queue",
    response_model=OutboxItem,
    tags=["Outbox & Safeguards"],
    summary="Queue or draft an outreach email",
    description="Persists a draft or explicit simulation. Live sending returns 503 until a provider is connected.",
    responses={503: {"description": "Live sending is not configured"}},
)
def queue_email(payload: QueueEmailRequest, outbox: OutboxDispatcherService = Depends(get_outbox)):
    """
    POST endpoint to queue or draft an outreach message.
    """
    try:
        return outbox.queue_message(payload)
    except LiveSendingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@router.get(
    "/items",
    response_model=List[OutboxItem],
    tags=["Outbox & Safeguards"],
    summary="List all outbox messages",
    description="Returns all tracked messages in the outreach pipeline, optionally filtered by status."
)
def list_outbox_items(
    status: Optional[OutboxStatus] = Query(default=None, description="Optional status filter: draft, sent, queued, etc."),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    outbox: OutboxDispatcherService = Depends(get_outbox),
):
    """
    GET endpoint to retrieve pipeline items.
    """
    return outbox.list_items(status=status, limit=limit, offset=offset)

@router.get(
    "/stats",
    response_model=OutboxStats,
    tags=["Outbox & Safeguards"],
    summary="Get sending quota & pipeline stats",
    description="Returns current daily limits, emails sent today, remaining quota, and total counts."
)
def get_outbox_stats(outbox: OutboxDispatcherService = Depends(get_outbox)):
    """
    GET endpoint to check delivery limits and safety quotas.
    """
    return outbox.get_stats()


@router.get("/items/{item_id}", response_model=OutboxItem, tags=["Outbox & Safeguards"])
def get_outbox_item(item_id: str, outbox: OutboxDispatcherService = Depends(get_outbox)):
    item = outbox.store.get_outbox(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Outbox item not found")
    return item
