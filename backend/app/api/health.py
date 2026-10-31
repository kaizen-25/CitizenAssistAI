from fastapi import APIRouter

from app.config import get_settings, load_schemes, verified_by_category
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health")
def health() -> HealthResponse:
    settings = get_settings()
    schemes = load_schemes()
    return HealthResponse(
        llm_provider=settings.llm_provider,
        llm_available=False,  # no provider is implemented until Phase 2
        demo_mode=settings.demo_mode,
        schemes_loaded=len(schemes),
        verified_by_category=verified_by_category(schemes),
        show_unverified=settings.show_unverified,
    )
