from __future__ import annotations

from fastapi.testclient import TestClient


def _mk_context(client: TestClient, name: str) -> str:
    r = client.post("/contexts", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def test_link_repo_dedup_and_events(client: TestClient):
    ctx_id = _mk_context(client, "ctx-repos")

    repo = {"provider": "github", "owner": "org", "name": "repo", "branch": "main"}
    r1 = client.post(f"/contexts/{ctx_id}/repos", json=repo)
    assert r1.status_code == 200
    ctx_after = r1.json()
    assert len(ctx_after["repos"]) == 1

    # link again: should not duplicate in context.repos
    r2 = client.post(f"/contexts/{ctx_id}/repos", json=repo)
    assert r2.status_code == 200
    ctx_after2 = r2.json()
    assert len(ctx_after2["repos"]) == 1

    # events include repo_linked (emitted per call; dedup is on stored repo list)
    r = client.get(f"/contexts/{ctx_id}/events")
    assert r.status_code == 200
    events = [e for e in r.json() if e["category"] == "repo" and e["type"] == "repo_linked"]
    assert len(events) >= 1


def test_link_repo_different_branches_are_distinct(client: TestClient):
    r = client.post("/contexts", json={"name": "ctx-repos-branches"})
    assert r.status_code == 200
    ctx_id = r.json()["id"]

    repo_main = {"provider": "github", "owner": "org", "name": "repo", "branch": "main"}
    repo_dev = {"provider": "github", "owner": "org", "name": "repo", "branch": "dev"}

    r1 = client.post(f"/contexts/{ctx_id}/repos", json=repo_main)
    assert r1.status_code == 200
    r2 = client.post(f"/contexts/{ctx_id}/repos", json=repo_dev)
    assert r2.status_code == 200
    ctx_after = r2.json()
    assert len(ctx_after["repos"]) == 2
