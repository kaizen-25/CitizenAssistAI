import json
from pathlib import Path

import pytest

from app.schemas import Scheme

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_schemes.json"


@pytest.fixture(scope="session")
def schemes() -> list[Scheme]:
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [Scheme.model_validate(record) for record in records]


@pytest.fixture(scope="session")
def by_id(schemes) -> dict[str, Scheme]:
    return {scheme.scheme_id: scheme for scheme in schemes}
