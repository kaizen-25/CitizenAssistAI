"""In-memory session store (dict + 2-hour TTL). Implemented in Phase 4."""

SESSION_TTL_SECONDS = 2 * 60 * 60


def create_session(language: str) -> str:
    raise NotImplementedError


def get_session(session_id: str) -> dict:
    raise NotImplementedError
