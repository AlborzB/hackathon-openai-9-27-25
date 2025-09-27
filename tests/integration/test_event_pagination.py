from __future__ import annotations

from fastapi.testclient import TestClient


def _mk_context(client: TestClient, name: str) -> str:
    r = client.post("/contexts", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def test_context_events_after_cursor(client: TestClient):
    ctx = _mk_context(client, "ctx-cursor")

    # generate several events in order
    r = client.post(f"/contexts/{ctx}/memories", json={"author": "A", "text": "m1"})
    assert r.status_code == 200
    r = client.post(f"/contexts/{ctx}/tasks", json={"title": "t1"})
    assert r.status_code == 200
    r = client.post(f"/contexts/{ctx}/tasks", json={"title": "t2"})
    assert r.status_code == 200

    # get all events and pick a middle cursor
    r = client.get(f"/contexts/{ctx}/events")
    assert r.status_code == 200
    all_events = r.json()
    assert len(all_events) >= 3
    mid_id = all_events[-2]["id"]  # cursor to second-to-last

    # fetch events strictly after mid_id → expect exactly the last one
    r = client.get(f"/contexts/{ctx}/events", params={"after": mid_id})
    assert r.status_code == 200
    after_events = r.json()
    assert len(after_events) == 1
    assert after_events[0]["id"] == all_events[-1]["id"]

    # unknown cursor returns full set (lenient behavior)
    r = client.get(f"/contexts/{ctx}/events", params={"after": "evt_nope"})
    assert r.status_code == 200
    assert len(r.json()) == len(all_events)


def test_run_events_after_cursor(client: TestClient):
    ctx = _mk_context(client, "ctx-cursor-run")
    r = client.post("/orchestrations", json={"context_id": ctx, "prompt": "plan"})
    assert r.status_code == 200
    run = r.json()

    r = client.get(f"/orchestrations/{run['id']}/events")
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 2  # user_message + plan
    first = events[0]

    # after=first.id should return the remaining events
    r = client.get(f"/orchestrations/{run['id']}/events", params={"after": first["id"]})
    assert r.status_code == 200
    rest = r.json()
    assert [e["id"] for e in rest] == [e["id"] for e in events[1:]]

    # after=last.id returns empty
    r = client.get(f"/orchestrations/{run['id']}/events", params={"after": events[-1]["id"]})
    assert r.status_code == 200
    assert r.json() == []

