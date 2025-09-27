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


def test_orchestration_events_filters_and_limit(client: TestClient):
    # setup a run
    r = client.post("/contexts", json={"name": "ctx-orch2"})
    assert r.status_code == 200
    ctx_id = r.json()["id"]
    r = client.post("/orchestrations", json={"context_id": ctx_id, "prompt": "X"})
    assert r.status_code == 200
    run_id = r.json()["id"]

    # filter by category=user
    r = client.get(f"/orchestrations/{run_id}/events", params={"category": "user"})
    assert r.status_code == 200
    events = r.json()
    assert all(e["category"] == "user" for e in events)

    # filter by type=plan
    r = client.get(f"/orchestrations/{run_id}/events", params={"type": "plan"})
    assert r.status_code == 200
    events = r.json()
    assert all(e["type"] == "plan" for e in events)

    # limit=1 returns last event
    r_all = client.get(f"/orchestrations/{run_id}/events")
    assert r_all.status_code == 200
    all_events = r_all.json()
    r_last = client.get(f"/orchestrations/{run_id}/events", params={"limit": 1})
    assert r_last.status_code == 200
    last_events = r_last.json()
    assert len(last_events) == 1
    assert last_events[0]["id"] == all_events[-1]["id"]


def test_orchestration_events_unknown_run_404(client: TestClient):
    r = client.get("/orchestrations/run_nope/events")
    assert r.status_code == 404
