from fastapi import APIRouter

from app.core.config import settings
from app.llm.factory import get_llm_provider

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def status():
    # Calling get_llm_provider() forces resolution (incl. mock fallback) so active_provider_name
    # is accurate even on the very first request after startup.
    get_llm_provider()
    from app.llm.factory import active_provider_name

    return {
        "llm_provider": active_provider_name,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "demo_mode": active_provider_name == "mock",
    }
