from fastapi import APIRouter, Request, Query

from webapp.dependencies import templates
from webapp.services.speaker_service import SpeakerService

router = APIRouter()


@router.get("")
async def speaker_list(
    request: Request,
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    """Speaker list with search"""
    limit = 50
    offset = (page - 1) * limit

    speakers = SpeakerService.get_all(name_search=q, limit=limit, offset=offset)
    top_speakers = SpeakerService.get_top_speakers(limit=20)

    return templates.TemplateResponse(
        "speakers/list.html",
        {
            "request": request,
            "speakers": speakers,
            "search_query": q,
            "page": page,
            "top_speakers": top_speakers,
        },
    )


@router.get("/{speaker_id}")
async def speaker_detail(
    request: Request,
    speaker_id: str,
    committee: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    """Speaker detail with speeches"""
    speaker = SpeakerService.get_by_id(speaker_id)
    if not speaker:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": "발언자를 찾을 수 없습니다."},
            status_code=404,
        )

    stats = SpeakerService.get_stats(speaker_id)
    limit = 30
    offset = (page - 1) * limit
    speeches = SpeakerService.get_speeches(
        speaker_id,
        class_name=committee,
        limit=limit,
        offset=offset,
    )
    activity = SpeakerService.get_activity_by_date(speaker_id)

    # Get unique committees for filter
    all_speeches = SpeakerService.get_speeches(speaker_id, limit=1000)
    committees = list(set(s["class_name"] for s in all_speeches if s["class_name"]))

    return templates.TemplateResponse(
        "speakers/detail.html",
        {
            "request": request,
            "speaker": speaker,
            "stats": stats,
            "speeches": speeches,
            "activity": activity,
            "committees": sorted(committees),
            "current_committee": committee,
            "page": page,
        },
    )
