from fastapi import Depends, Request

from app.core.storage import SQLiteStore
from app.services.outbox_dispatcher import OutboxDispatcherService


def get_store(request: Request) -> SQLiteStore:
    return request.app.state.store


def get_outbox(store: SQLiteStore = Depends(get_store)) -> OutboxDispatcherService:
    return OutboxDispatcherService(store)
