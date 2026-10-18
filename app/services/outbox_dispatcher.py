from datetime import datetime, timezone
from uuid import uuid4

from app.core.storage import SQLiteStore
from app.schemas.outbox import DispatchMode, OutboxItem, OutboxStatus, QueueEmailRequest


class LiveSendingUnavailableError(RuntimeError):
    """No delivery provider exists yet; never manufacture a success result."""


class OutboxDispatcherService:
    """Persist drafts and simulations. Delivery remains a separate future capability."""

    def __init__(self, store: SQLiteStore):
        self.store = store

    def get_sent_today_count(self):
        return self.store.outbox_stats().sent_today

    def get_stats(self):
        return self.store.outbox_stats()

    def queue_message(self, request: QueueEmailRequest) -> OutboxItem:
        if request.mode == DispatchMode.LIVE_SEND:
            raise LiveSendingUnavailableError("Live sending is unavailable. Save a draft or choose simulate; no mail provider is connected.")
        simulated = request.mode == DispatchMode.SIMULATE
        item = OutboxItem(
            id=str(uuid4()), recipient_email=request.recipient_email,
            recipient_name=request.recipient_name, company_name=request.company_name,
            subject_line=request.subject_line, body=request.body,
            status=OutboxStatus.SIMULATED if simulated else OutboxStatus.DRAFT,
            created_at=datetime.now(timezone.utc), sent_at=None,
            note="Simulation saved. No email was sent or scheduled." if simulated else "Draft saved. No email was sent.",
        )
        # A successful response is returned only after the database commits.
        return self.store.save_outbox(item)

    def list_items(self, status=None, limit=50, offset=0):
        return self.store.list_outbox(status, limit, offset)
