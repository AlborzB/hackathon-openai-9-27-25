from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from memory_broker.main import create_app


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c

