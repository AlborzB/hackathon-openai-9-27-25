from __future__ import annotations

from fastapi.testclient import TestClient


def _mk_context(client: TestClient, name: str) -> str:
    r = client.post("/contexts", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def test_plan_parser_rejects_unknown_action(client: TestClient):
    ctx = _mk_context(client, "ctx-plan-parse")

    bad_plan = {
        "version": "1",
        "agents": [],
        "actions": [
            {"type": "not_real", "foo": 1}
        ],
    }

    r = client.post(
        "/orchestrations",
        json={"context_id": ctx, "prompt": "do stuff", "plan": bad_plan},
    )
    # Pydantic should reject the payload before hitting the handler
    assert r.status_code == 422


def test_orchestrator_executes_plan_and_emits_events(client: TestClient):
    ctx = _mk_context(client, "ctx-orch")

    plan = {
        "version": "1",
        "agents": [
            {"name": "backend"},
        ],
        "actions": [
            {"type": "create_agent", "spec": {"name": "frontend"}},
            {"type": "message", "agent_id": "frontend", "content": "hello from agent"},
            {"type": "task.create", "context_id": ctx, "payload": {"title": "Implement API", "assignee": "backend", "tags": ["feat"]}},
            {"type": "handoff", "payload": {"from": "backend", "to": "frontend", "context": ctx, "task": "task_temp", "summary": "hand over"}},
            {"type": "subprocess.run", "command": ["echo", "ok"], "cwd": "."},
        ],
    }

    # We don't know the task id before creation; adjust handoff payload after task create via two-step run is complex.
    # Simplify by first creating a task through API, then reference it in the handoff action.
    r_task = client.post(f"/contexts/{ctx}/tasks", json={"title": "bootstrap", "assignee": "bootstrapper"})
    assert r_task.status_code == 200
    pre_task_id = r_task.json()["id"]
    # patch plan to use real task id
    for a in plan["actions"]:
        if a["type"] == "handoff":
            a["payload"]["task"] = pre_task_id

    r = client.post(
        "/orchestrations",
        json={"context_id": ctx, "prompt": "execute plan", "plan": plan},
    )
    assert r.status_code == 200
    run = r.json()

    # Run should be completed because we execute synchronously when plan is provided
    r2 = client.get(f"/orchestrations/{run['id']}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"

    # Events should include user_message + plan placeholder + run_started + action events + domain events + run_completed
    r3 = client.get(f"/orchestrations/{run['id']}/events")
    assert r3.status_code == 200
    events = r3.json()
    types = [e["type"] for e in events]

    assert "user_message" in types
    assert "plan" in types
    assert "run_started" in types
    assert "action_start" in types
    assert "action_end" in types
    assert "agent_created" in types
    assert "task_created" in types
    assert "handoff_recorded" in types
    assert "subprocess_started" in types
    assert "subprocess_completed" in types
    assert "run_completed" in types

