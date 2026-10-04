import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional

from app.schemas.outbox import (
    DispatchMode, 
    OutboxStatus, 
    QueueEmailRequest, 
    OutboxItem, 
    OutboxStats
)
from app.core.config import settings

class OutboxDispatcherService:
    """
    Outbox Dispatcher & Deliverability Guardian.
    Manages cold email dispatch, enforces strict daily send caps to avoid spam blacklists,
    and supports safe 'Draft First' workflows.
    """

    def __init__(self, daily_limit: int = 20):
        self.daily_limit = daily_limit
        # In-memory storage for pipeline tracking (can be persisted to SQLite/database)
        self._outbox: Dict[str, OutboxItem] = {}

    def get_sent_today_count(self) -> int:
        """
        Calculates how many emails have been sent today (UTC).
        """
        today = datetime.now(timezone.utc).date()
        count = 0
        for item in self._outbox.values():
            if item.status == OutboxStatus.SENT and item.sent_at:
                if item.sent_at.date() == today:
                    count += 1
        return count

    def get_stats(self) -> OutboxStats:
        """
        Returns live dispatch metrics and safeguard limits.
        """
        sent_today = self.get_sent_today_count()
        remaining = max(0, self.daily_limit - sent_today)
        
        drafts = sum(1 for i in self._outbox.values() if i.status == OutboxStatus.DRAFT)
        queued = sum(1 for i in self._outbox.values() if i.status in (OutboxStatus.QUEUED, OutboxStatus.QUEUED_FOR_TOMORROW))
        total_sent = sum(1 for i in self._outbox.values() if i.status == OutboxStatus.SENT)

        return OutboxStats(
            daily_limit=self.daily_limit,
            sent_today=sent_today,
            remaining_today=remaining,
            total_drafts=drafts,
            total_queued=queued,
            total_sent=total_sent
        )

    def queue_message(self, request: QueueEmailRequest) -> OutboxItem:
        """
        Queues or drafts an outreach message with automated rate-limit safeguards.
        """
        item_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc)

        # Mode 1: Draft Mode (Safe review mode)
        if request.mode == DispatchMode.DRAFT:
            item = OutboxItem(
                id=item_id,
                recipient_email=request.recipient_email,
                recipient_name=request.recipient_name,
                company_name=request.company_name,
                subject_line=request.subject_line,
                body=request.body,
                status=OutboxStatus.DRAFT,
                created_at=now,
                note="Saved as reviewable draft. Ready to inspect before sending."
            )
            self._outbox[item_id] = item
            return item

        # Mode 2: Live Send Mode
        sent_today = self.get_sent_today_count()
        if sent_today >= self.daily_limit:
            # Safeguard triggered! Prevent spam flagging by holding until tomorrow
            item = OutboxItem(
                id=item_id,
                recipient_email=request.recipient_email,
                recipient_name=request.recipient_name,
                company_name=request.company_name,
                subject_line=request.subject_line,
                body=request.body,
                status=OutboxStatus.QUEUED_FOR_TOMORROW,
                created_at=now,
                note=f"Daily safeguard limit ({self.daily_limit}/day) reached. Held in queue for tomorrow to protect domain reputation."
            )
            self._outbox[item_id] = item
            return item

        # Within safe daily limit: dispatch!
        item = OutboxItem(
            id=item_id,
            recipient_email=request.recipient_email,
            recipient_name=request.recipient_name,
            company_name=request.company_name,
            subject_line=request.subject_line,
            body=request.body,
            status=OutboxStatus.SENT,
            created_at=now,
            sent_at=now,
            note="Dispatched successfully within daily rate limits."
        )
        self._outbox[item_id] = item
        return item

    def list_items(self, status: Optional[OutboxStatus] = None) -> List[OutboxItem]:
        """
        Lists all outbox items, optionally filtered by status.
        """
        items = list(self._outbox.values())
        if status:
            items = [i for i in items if i.status == status]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

# Singleton instance initialized with configurable limit
outbox_dispatcher_service = OutboxDispatcherService(daily_limit=settings.DAILY_SEND_LIMIT)
