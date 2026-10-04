from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class DispatchMode(str, Enum):
    """
    How the user wants the outreach message handled.
    """
    DRAFT = "draft"          # Safe mode: saves to reviewable outbox / Gmail drafts
    LIVE_SEND = "live_send"  # Sends automatically if within daily rate limits

class OutboxStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    QUEUED_FOR_TOMORROW = "queued_for_tomorrow"
    SENT = "sent"
    FAILED = "failed"

class QueueEmailRequest(BaseModel):
    """
    Input to queue or draft an email.
    """
    recipient_email: str = Field(..., examples=["sarah.jenkins@stripe.com"])
    recipient_name: str = Field(..., examples=["Sarah Jenkins"])
    company_name: str = Field(..., examples=["Stripe"])
    subject_line: str = Field(..., examples=["Quick note regarding Full-Stack Engineer @ Stripe"])
    body: str
    mode: DispatchMode = Field(default=DispatchMode.DRAFT)

class OutboxItem(BaseModel):
    """
    A single tracked message in our outreach pipeline.
    """
    id: str
    recipient_email: str
    recipient_name: str
    company_name: str
    subject_line: str
    body: str
    status: OutboxStatus
    created_at: datetime
    sent_at: Optional[datetime] = None
    note: Optional[str] = None

class OutboxStats(BaseModel):
    """
    Safeguards & sending velocity metrics.
    """
    daily_limit: int
    sent_today: int
    remaining_today: int
    total_drafts: int
    total_queued: int
    total_sent: int
