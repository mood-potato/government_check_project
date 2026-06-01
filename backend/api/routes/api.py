from typing import Any

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from backend.api.services.home_service import HomeService
from backend.api.services.member_service import MemberService
from backend.api.services.meeting_service import MeetingService
from backend.api.services.speaker_service import SpeakerService
from backend.api.dependencies import get_search_service

router = APIRouter()


@router.get("/home")
async def get_home() -> dict[str, Any]:
    """API: Get home page data"""
    return HomeService.get_home()


@router.get("/home/hero")
async def get_home_hero() -> dict[str, Any] | None:
    """API: Get precomputed home hero data"""
    return HomeService.get_home_hero()


@router.get("/home/recent-cases")
async def get_home_recent_cases() -> list[dict[str, Any]]:
    """API: Get home recent analysis cases"""
    return HomeService.get_recent_cases()


@router.get("/home/featured-members")
async def get_home_featured_members() -> list[dict[str, Any]]:
    """API: Get home featured members"""
    return HomeService.get_featured_members()


@router.get("/members")
async def get_members(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """API: Get member profile list page data"""
    return MemberService.get_members(limit=limit, offset=offset)


@router.get("/members/{member_slug}")
async def get_member(member_slug: str) -> dict[str, Any]:
    """API: Get member detail page data"""
    member = MemberService.get_member_detail(member_slug)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


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
