from __future__ import annotations

from fastapi.testclient import TestClient

from memory_broker.main import create_app


def test_background_planner_emits_events_sequence():
    app = create_app()
    with TestClient(app) as client:
        # Arrange: make a context
        r = client.post("/contexts", json={"name": "ctx-bg"})
        assert r.status_code == 200
        ctx = r.json()["id"]

        # Act: create orchestration WITHOUT an inline plan (background planner path)
        r = client.post("/orchestrations", json={"context_id": ctx, "prompt": "Do a thing"})
        assert r.status_code == 200
        run = r.json()

        # Fetch events; background task runs after response, so loop a few times without sleeping
        seen_types = set()
        for _ in range(5):
            r = client.get(f"/orchestrations/{run['id']}/events")
            assert r.status_code == 200
            evts = r.json()
            seen_types.update(e["type"] for e in evts)
            if "run_completed" in seen_types or "run_failed" in seen_types:
                break

        # Assert subset of expected types observed
        assert {"user_message", "plan"}.issubset(seen_types)
        assert "plan_ready" in seen_types  # produced by background planner
        assert "run_started" in seen_types
        assert ("run_completed" in seen_types) or ("run_failed" in seen_types)

