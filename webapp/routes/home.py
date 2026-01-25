from fastapi import APIRouter, Request

from webapp.dependencies import templates
from webapp.services.meeting_service import MeetingService

router = APIRouter()


@router.get("/")
async def home(request: Request):
    """Home dashboard with stats and recent meetings"""
    stats = MeetingService.get_stats()
    meetings = MeetingService.get_all(limit=20)
    filters = MeetingService.get_filter_options()

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "stats": stats,
            "meetings": meetings,
            "filters": filters,
        },
    )
