"""Saved snapshots have stable IDs and timestamps so they can be reopened later."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.pitch import CandidateProfile
from app.schemas.recruiter import DiscoverRecruitersRequest, DiscoverRecruitersResponse


class SavedProfile(BaseModel):
    id: str
    created_at: datetime
    candidate: CandidateProfile


class SavedDiscovery(BaseModel):
    id: str
    created_at: datetime
    request: DiscoverRecruitersRequest
    result: DiscoverRecruitersResponse


class HistoryEvent(BaseModel):
    id: int
    record_id: str
    kind: Literal["profile", "discovery", "outbox"]
    action: str
    created_at: datetime
