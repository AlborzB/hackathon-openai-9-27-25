from __future__ import annotations

from fastapi.testclient import TestClient


def _mk_context(client: TestClient, name: str) -> str:
    r = client.post("/contexts", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def test_memories_create_and_list_and_events(client: TestClient):
    ctx_id = _mk_context(client, "ctx-memories")

    # add memory
    r = client.post(
        f"/contexts/{ctx_id}/memories",
        json={"author": "Alice", "text": "Initial setup", "tags": ["init"]},
    )
    assert r.status_code == 200
    mem = r.json()
    assert mem["context_id"] == ctx_id
    assert mem["text"] == "Initial setup"

    # list memories
    r = client.get(f"/contexts/{ctx_id}/memories")
    assert r.status_code == 200
    items = r.json()
    assert any(i["id"] == mem["id"] for i in items)

    # events include memory_added
    r = client.get(f"/contexts/{ctx_id}/events")
    assert r.status_code == 200
    events = r.json()
    assert any(e["category"] == "memory" and e["type"] == "memory_added" for e in events)


def test_tasks_create_update_list_and_events(client: TestClient):
    ctx_id = _mk_context(client, "ctx-tasks")

    # create task
    r = client.post(
        f"/contexts/{ctx_id}/tasks",
        json={"title": "Do thing", "description": "desc", "assignee": "Alice"},
    )
    assert r.status_code == 200
    task = r.json()
    assert task["context_id"] == ctx_id

    # update task
    r = client.patch(
        f"/contexts/{ctx_id}/tasks/{task['id']}",
        json={"status": "in_progress"},
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["status"] == "in_progress"

    # list tasks
    r = client.get(f"/contexts/{ctx_id}/tasks")
    assert r.status_code == 200
    tasks = r.json()
    assert any(t["id"] == task["id"] for t in tasks)

    # events include task_created + task_updated
    r = client.get(f"/contexts/{ctx_id}/events")
    assert r.status_code == 200
    events = r.json()
    kinds = {(e["category"], e["type"]) for e in events}
    assert ("task", "task_created") in kinds
    assert ("task", "task_updated") in kinds


def test_handoffs_record_list_and_events(client: TestClient):
    ctx_id = _mk_context(client, "ctx-handoffs")

    # need a task id to handoff
    r = client.post(f"/contexts/{ctx_id}/tasks", json={"title": "Handoff task"})
    assert r.status_code == 200
    task = r.json()

    ho_payload = {
        "from": "Alice",
        "to": "Bob",
        "context": ctx_id,
        "task": task["id"],
        "summary": "Please continue",
    }
    r = client.post("/handoffs", json=ho_payload)
    assert r.status_code == 200
    ho = r.json()
    assert ho["context_id"] == ctx_id
    assert ho["task_id"] == task["id"]

    # list handoffs
    r = client.get(f"/contexts/{ctx_id}/handoffs")
    assert r.status_code == 200
    handoffs = r.json()
    assert any(h["id"] == ho["id"] for h in handoffs)

    # events include handoff_recorded
    r = client.get(f"/contexts/{ctx_id}/events")
    assert r.status_code == 200
    events = r.json()
    assert any(e["category"] == "handoff" and e["type"] == "handoff_recorded" for e in events)

