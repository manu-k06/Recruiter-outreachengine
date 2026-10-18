"""Explicitly save confirmed profiles and reopen durable snapshots."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_store
from app.core.storage import SQLiteStore
from app.schemas.pitch import CandidateProfile
from app.schemas.storage import SavedProfile, SavedDiscovery, HistoryEvent

router = APIRouter(tags=["Saved data"])


@router.post("/profiles", response_model=SavedProfile, status_code=201)
def save_profile(candidate: CandidateProfile, store: SQLiteStore = Depends(get_store)):
    """Save a candidate-confirmed snapshot. Parsing alone does not save or confirm a profile."""
    return store.save_profile(candidate)


@router.get("/profiles", response_model=list[SavedProfile])
def list_profiles(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), store: SQLiteStore = Depends(get_store)):
    return store.list_profiles(limit, offset)


@router.get("/profiles/{profile_id}", response_model=SavedProfile)
def get_profile(profile_id: str, store: SQLiteStore = Depends(get_store)):
    result = store.get_profile(profile_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/discoveries", response_model=list[SavedDiscovery])
def list_discoveries(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), store: SQLiteStore = Depends(get_store)):
    return store.list_discoveries(limit, offset)


@router.get("/discoveries/{discovery_id}", response_model=SavedDiscovery)
def get_discovery(discovery_id: str, store: SQLiteStore = Depends(get_store)):
    result = store.get_discovery(discovery_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Discovery not found")
    return result


@router.get("/history", response_model=list[HistoryEvent])
def history(record_id: str | None = None, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), store: SQLiteStore = Depends(get_store)):
    return store.history(record_id, limit, offset)
