from __future__ import annotations

from fastapi.testclient import TestClient

from memory_broker.main import create_app


def test_cancel_orchestration_marks_status_and_emits_event():
    app = create_app()
    with TestClient(app) as client:
        # Create context and run (background planner path)
        r = client.post("/contexts", json={"name": "ctx-cancel"})
        assert r.status_code == 200
        ctx = r.json()["id"]

        r = client.post("/orchestrations", json={"context_id": ctx, "prompt": "Cancel me"})
        assert r.status_code == 200
        run = r.json()

        # Cancel the run
        r = client.post(f"/orchestrations/{run['id']}/cancel")
        assert r.status_code == 200
        canceled = r.json()
        assert canceled["status"] == "canceled"

        # Events should include run_canceled
        r = client.get(f"/orchestrations/{run['id']}/events")
        assert r.status_code == 200
        types = [e["type"] for e in r.json()]
        assert "run_canceled" in types

