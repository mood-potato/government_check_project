from fastapi import APIRouter, Request, Query

from webapp.dependencies import templates
from webapp.services.meeting_service import MeetingService

router = APIRouter()


@router.get("")
async def meeting_list(
    request: Request,
    committee: str | None = Query(None),
    session: int | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    """Meeting list with filters"""
    limit = 30
    offset = (page - 1) * limit

    meetings = MeetingService.get_all(
        class_name=committee,
        dae_number=session,
        title_search=q,
        limit=limit,
        offset=offset,
    )
    filters = MeetingService.get_filter_options()

    return templates.TemplateResponse(
        "meetings/list.html",
        {
            "request": request,
            "meetings": meetings,
            "filters": filters,
            "current_filters": {
                "committee": committee,
                "session": session,
                "q": q,
            },
            "page": page,
        },
    )


@router.get("/{pdf_url_id}")
async def meeting_detail(
    request: Request,
    pdf_url_id: str,
    speaker: str | None = Query(None),
):
    """Meeting detail with speeches"""
    meeting = MeetingService.get_by_id(pdf_url_id)
    if not meeting:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": "회의를 찾을 수 없습니다."},
            status_code=404,
        )

    all_speeches = MeetingService.get_speeches(pdf_url_id)
    speeches = all_speeches

    # Filter by speaker if specified
    if speaker:
        speeches = [s for s in all_speeches if s["speaker"] == speaker]

    # Calculate speaker distribution for chart
    speaker_counts = {}
    for s in all_speeches:
        speaker_counts[s["speaker"]] = speaker_counts.get(s["speaker"], 0) + 1

    speaker_chart_data = sorted(
        speaker_counts.items(), key=lambda x: x[1], reverse=True
    )[:15]

    return templates.TemplateResponse(
        "meetings/detail.html",
        {
            "request": request,
            "meeting": meeting,
            "speeches": speeches,
            "speaker_filter": speaker,
            "speakers": list(speaker_counts.keys()),
            "chart_data": speaker_chart_data,
            "stats": {
                "total_speeches": len(all_speeches),
                "total_speakers": len(speaker_counts),
            },
        },
    )
