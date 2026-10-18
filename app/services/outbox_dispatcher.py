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

class LiveSendingUnavailableError(RuntimeError):
    """No delivery provider exists yet; never manufacture a success result."""


class OutboxDispatcherService:
    """
    Temporary draft and simulation storage. No email is delivered by this service.
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
            total_sent=total_sent,
            total_simulated=sum(i.status == OutboxStatus.SIMULATED for i in self._outbox.values()),
        )

    def queue_message(self, request: QueueEmailRequest) -> OutboxItem:
        """
        Save a draft or an explicitly simulated message without recording delivery.
        """
        # Reject before creating any record so failed requests cannot look delivered.
        if request.mode == DispatchMode.LIVE_SEND:
            raise LiveSendingUnavailableError("Live sending is unavailable. Save a draft or choose simulate; no mail provider is connected.")
        item_id = str(uuid.uuid4())
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
                note="Draft stored in memory only; it will be lost on restart. No email was sent."
            )
            self._outbox[item_id] = item
            return item

        # Simulation never consumes real sending quota or schedules future delivery.
        item = OutboxItem(
            id=item_id,
            recipient_email=request.recipient_email,
            recipient_name=request.recipient_name,
            company_name=request.company_name,
            subject_line=request.subject_line,
            body=request.body,
            status=OutboxStatus.SIMULATED,
            created_at=now,
            sent_at=None,
            note="Simulation only. No email was sent or scheduled. This record is lost on restart."
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
