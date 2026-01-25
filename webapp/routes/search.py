from fastapi import APIRouter, Request, Query

from webapp.dependencies import templates, get_search_service

router = APIRouter()


@router.get("")
async def search_page(
    request: Request,
    q: str | None = Query(None),
    top_k: int = Query(10, ge=5, le=50),
    threshold: float = Query(0.3, ge=0.0, le=1.0),
    speaker: str | None = Query(None),
):
    """Search page with optional query parameters"""
    results = []
    search_service = get_search_service()

    if q and search_service:
        results = search_service.search(
            query=q,
            top_k=top_k,
            speaker=speaker if speaker else None,
            score_threshold=threshold,
        )

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "query": q,
            "results": results,
            "top_k": top_k,
            "threshold": threshold,
            "speaker_filter": speaker,
            "search_available": search_service is not None,
        },
    )
