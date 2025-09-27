from __future__ import annotations

from fastapi.testclient import TestClient


def _mk_context(client: TestClient, name: str) -> str:
    r = client.post("/contexts", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def test_orchestration_creation_emits_events(client: TestClient):
    ctx_id = _mk_context(client, "ctx-orch")

    # create orchestration
    payload = {"context_id": ctx_id, "prompt": "Build a demo app"}
    r = client.post("/orchestrations", json=payload)
    assert r.status_code == 200
    run = r.json()
    assert run["context_id"] == ctx_id
    assert run["status"] in ("pending", "running", "completed", "failed")

    # fetch run
    r = client.get(f"/orchestrations/{run['id']}")
    assert r.status_code == 200

    # list run events: expect user_message then plan placeholder
    r = client.get(f"/orchestrations/{run['id']}/events")
    assert r.status_code == 200
    events = r.json()
    kinds = [(e["category"], e["type"]) for e in events]
    assert ("user", "user_message") in kinds
    assert ("plan", "plan") in kinds

    # context events also contain them
    r = client.get(f"/contexts/{ctx_id}/events")
    assert r.status_code == 200
    ctx_events = r.json()
    ckinds = {(e["category"], e["type"]) for e in ctx_events}
    assert ("user", "user_message") in ckinds
    assert ("plan", "plan") in ckinds

