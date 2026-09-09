from fastapi import APIRouter

from backend.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.API_TITLE,
    }
