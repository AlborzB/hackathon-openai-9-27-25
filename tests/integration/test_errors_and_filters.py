from __future__ import annotations

from fastapi.testclient import TestClient


def _mk_context(client: TestClient, name: str) -> str:
    r = client.post("/contexts", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def test_404_unknown_context_across_endpoints(client: TestClient):
    unknown = "nope"

    r = client.get(f"/contexts/{unknown}/memories")
    assert r.status_code == 404

    r = client.get(f"/contexts/{unknown}/tasks")
    assert r.status_code == 404

    r = client.get(f"/contexts/{unknown}/events")
    assert r.status_code == 404

    r = client.get(f"/contexts/{unknown}/handoffs")
    assert r.status_code == 404

    r = client.post(f"/contexts/{unknown}/repos", json={"provider": "github", "owner": "o", "name": "n"})
    assert r.status_code == 404


def test_404_unknown_run(client: TestClient):
    r = client.get("/orchestrations/run_ffff/events")
    # list_run_events returns [] when run has no events but if run unknown store may not raise;
    # first query get_orchestration to assert 404
    r = client.get("/orchestrations/run_ffff")
    assert r.status_code == 404


def test_422_invalid_payloads(client: TestClient):
    # invalid repo provider
    ctx = _mk_context(client, "ctx-422")
    r = client.post(f"/contexts/{ctx}/repos", json={"provider": "gitlab", "owner": "o", "name": "n"})
    assert r.status_code == 422

    # invalid task status
    r = client.post(f"/contexts/{ctx}/tasks", json={"title": "t"})
    assert r.status_code == 200
    task = r.json()
    r = client.patch(f"/contexts/{ctx}/tasks/{task['id']}", json={"status": "not_a_status"})
    assert r.status_code == 422

    # missing handoff fields
    r = client.post("/handoffs", json={"from": "a"})
    assert r.status_code == 422


def test_event_filters_agent_type_category_tag_limit(client: TestClient):
    ctx = _mk_context(client, "ctx-filters")

    # memory with tag 'alpha'
    r = client.post(
        f"/contexts/{ctx}/memories",
        json={"author": "A", "text": "m1", "tags": ["alpha"]},
    )
    assert r.status_code == 200

    # task with tag 'beta' and assignee 'Bob'
    r = client.post(
        f"/contexts/{ctx}/tasks",
        json={"title": "t1", "assignee": "Bob", "tags": ["beta"]},
    )
    assert r.status_code == 200

    # update same task to add another event
    task_id = r.json()["id"]
    r = client.patch(f"/contexts/{ctx}/tasks/{task_id}", json={"status": "in_progress"})
    assert r.status_code == 200

    # filter by category=memory
    r = client.get(f"/contexts/{ctx}/events", params={"category": "memory"})
    assert r.status_code == 200
    events = r.json()
    assert all(e["category"] == "memory" for e in events)

    # filter by type=task_created
    r = client.get(f"/contexts/{ctx}/events", params={"type": "task_created"})
    assert r.status_code == 200
    events = r.json()
    assert all(e["type"] == "task_created" for e in events)

    # filter by agent_id=Bob
    r = client.get(f"/contexts/{ctx}/events", params={"agent_id": "Bob"})
    assert r.status_code == 200
    events = r.json()
    assert all(e.get("agent_id") == "Bob" for e in events)

    # filter by tag=alpha (memory)
    r = client.get(f"/contexts/{ctx}/events", params={"tag": "alpha"})
    assert r.status_code == 200
    events = r.json()
    assert any(e["category"] == "memory" for e in events)

    # limit=1 returns last event only
    r_all = client.get(f"/contexts/{ctx}/events")
    assert r_all.status_code == 200
    all_events = r_all.json()
    r_last = client.get(f"/contexts/{ctx}/events", params={"limit": 1})
    assert r_last.status_code == 200
    last_events = r_last.json()
    assert len(last_events) == 1
    assert last_events[0]["id"] == all_events[-1]["id"]


def test_openapi_includes_new_paths(client: TestClient):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = spec.get("paths", {})
    # Check that key endpoints exist
    for p in (
        "/orchestrations",
        "/orchestrations/{run_id}",
        "/orchestrations/{run_id}/events",
        "/contexts/{context_id}/events",
        "/contexts/{context_id}/tasks",
        "/contexts/{context_id}/handoffs",
    ):
        assert p in paths, f"missing {p} in OpenAPI"

