from __future__ import annotations

from fastapi.testclient import TestClient


def test_upsert_agent_and_list(client: TestClient):
    # upsert agent
    r = client.post("/agents", json={"name": "Alice", "kind": "agent"})
    assert r.status_code == 200, r.text
    agent = r.json()
    assert agent["id"]
    assert agent["name"] == "Alice"

    # list agents
    r = client.get("/agents")
    assert r.status_code == 200
    agents = r.json()
    assert any(a["name"] == "Alice" for a in agents)


def test_create_context_and_list(client: TestClient):
    # create context
    r = client.post("/contexts", json={"name": "ctx-agents"})
    assert r.status_code == 200
    ctx = r.json()
    assert ctx["id"] == "ctx-agents"

    # list contexts
    r = client.get("/contexts")
    assert r.status_code == 200
    contexts = r.json()
    assert any(c["id"] == "ctx-agents" for c in contexts)

