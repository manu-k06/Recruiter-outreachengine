from pydantic import BaseModel, EmailStr, Field
from app.schemas.inputs import ShortText, BodyText
from typing import List, Optional
from datetime import datetime
from enum import Enum

class DispatchMode(str, Enum):
    """
    How the user wants the outreach message handled.
    """
    DRAFT = "draft"          # Persisted locally, not in a mail account.
    SIMULATE = "simulate"    # Preview dispatch without sending or using quota.
    LIVE_SEND = "live_send"  # Rejected until a real provider is configured.

class OutboxStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    QUEUED_FOR_TOMORROW = "queued_for_tomorrow"
    SENT = "sent"
    FAILED = "failed"
    SIMULATED = "simulated"

class QueueEmailRequest(BaseModel):
    """
    Input to queue or draft an email.
    """
    recipient_email: EmailStr = Field(..., examples=["sarah.jenkins@stripe.com"])
    recipient_name: ShortText = Field(..., examples=["Sarah Jenkins"])
    company_name: ShortText = Field(..., examples=["Stripe"])
    subject_line: ShortText = Field(..., examples=["Quick note regarding Full-Stack Engineer @ Stripe"])
    body: BodyText
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
    profile_id: Optional[str] = None
    discovery_id: Optional[str] = None
    lead_index: Optional[int] = None
    version: int = 1
    updated_at: Optional[datetime] = None

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
    total_simulated: int = 0
