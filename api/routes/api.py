from typing import Any

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from api.services.meeting_service import MeetingService
from api.services.speaker_service import SpeakerService
from api.dependencies import get_search_service

router = APIRouter()


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """API: Get dashboard statistics"""
    return MeetingService.get_stats()


@router.get("/meetings")
async def get_meetings(
    committee: str | None = None,
    session: int | None = None,
    q: str | None = None,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """API: Get meetings list"""
    return MeetingService.get_all(
        class_name=committee,
        dae_number=session,
        title_search=q,
        limit=limit,
        offset=offset,
    )


@router.get("/speakers")
async def get_speakers(
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """API: Get speakers list"""
    return SpeakerService.get_all(name_search=q, limit=limit, offset=offset)


class SearchQuery(BaseModel):
    query: str
    top_k: int = 10
    score_threshold: float = 0.3
    speaker: str | None = None


@router.post("/search")
async def search(req: SearchQuery) -> list[dict[str, Any]]:
    """API: Semantic search"""
    search_service = get_search_service()
    if not search_service:
        raise HTTPException(status_code=503, detail="Search service unavailable")

    return search_service.search(
        query=req.query,
        top_k=req.top_k,
        speaker=req.speaker,
        score_threshold=req.score_threshold,
    )
