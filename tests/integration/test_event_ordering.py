from __future__ import annotations

from fastapi.testclient import TestClient


def test_context_event_ordering_and_limit(client: TestClient):
    # Arrange
    r = client.post("/contexts", json={"name": "ctx-order"})
    assert r.status_code == 200
    ctx_id = r.json()["id"]

    # Perform several actions in order
    r = client.post(f"/contexts/{ctx_id}/memories", json={"author": "A", "text": "m1"})
    assert r.status_code == 200
    r = client.post(f"/contexts/{ctx_id}/tasks", json={"title": "t1", "assignee": "B"})
    assert r.status_code == 200
    task_id = r.json()["id"]
    r = client.patch(f"/contexts/{ctx_id}/tasks/{task_id}", json={"status": "in_progress"})
    assert r.status_code == 200
    r = client.post("/handoffs", json={"from": "A", "to": "B", "context": ctx_id, "task": task_id, "summary": "go"})
    assert r.status_code == 200

    # Fetch all events and ensure chronological order reflects action sequence
    r = client.get(f"/contexts/{ctx_id}/events")
    assert r.status_code == 200
    events = r.json()

    # Find indices of each event type
    def idx(cat, typ):
        for i, e in enumerate(events):
            if e["category"] == cat and e["type"] == typ:
                return i
        return None

    i_mem_added = idx("memory", "memory_added")
    i_task_created = idx("task", "task_created")
    i_task_updated = idx("task", "task_updated")
    i_handoff = idx("handoff", "handoff_recorded")

    assert None not in (i_mem_added, i_task_created, i_task_updated, i_handoff)
    assert i_mem_added < i_task_created < i_task_updated < i_handoff

    # limit=2 returns last two events in the same order
    r = client.get(f"/contexts/{ctx_id}/events", params={"limit": 2})
    assert r.status_code == 200
    last_two = r.json()
    assert len(last_two) == 2
    assert last_two[0]["id"] == events[-2]["id"]
    assert last_two[1]["id"] == events[-1]["id"]

