#!/usr/bin/env python3
"""
Simulate a multi-agent handoff via the Memory Broker HTTP API using only the stdlib.

Prereqs:
  uvicorn memory_broker.main:app --reload --port 7070

Run:
  python examples/multi_agent_handoff/run.py

Config:
  BASE_URL (default: http://localhost:7070)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict


BASE_URL = os.getenv("BASE_URL", "http://localhost:7070").rstrip("/")


def http(method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)
    except urllib.error.HTTPError as e:
        details = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code} {method} {path}: {details}") from None


def main() -> int:
    print(f"Using broker at {BASE_URL}")

    # 1) Upsert agents
    riley = http("POST", "/agents", {"name": "Riley", "kind": "human"})
    kai = http("POST", "/agents", {"name": "Kai", "kind": "human"})
    print(f"Agents: riley={riley['id']} kai={kai['id']}")

    # 2) Create context
    ctx = http("POST", "/contexts", {"name": "alpha-sprint", "description": "Week 2 delivery"})
    ctx_id = ctx["id"]
    print(f"Context created: {ctx_id}")

    # 3) Link repo (GitHub provider)
    ctx = http(
        "POST",
        f"/contexts/{urllib.parse.quote(ctx_id)}/repos",
        {"provider": "github", "owner": "org", "name": "app", "branch": "main"},
    )
    print(f"Repo linked: {ctx['repos'][-1]['owner']}/{ctx['repos'][-1]['name']}@{ctx['repos'][-1].get('branch')}")

    # 4) Create task
    task = http(
        "POST",
        f"/contexts/{urllib.parse.quote(ctx_id)}/tasks",
        {"title": "Fix auth redirect", "description": "Handle 302 loop", "assignee": riley["id"]},
    )
    task_id = task["id"]
    print(f"Task created: {task_id}")

    # 5) Append memory (progress note)
    mem = http(
        "POST",
        f"/contexts/{urllib.parse.quote(ctx_id)}/memories",
        {
            "author": riley["id"],
            "text": "Auth flow patched; added state param and tests",
            "tags": ["auth", "bugfix"],
            "refs": [{"type": "file", "value": "src/auth/redirect.ts"}],
        },
    )
    print(f"Memory appended: {mem['id']}")

    # 6) Move task to review
    task = http(
        "PATCH",
        f"/contexts/{urllib.parse.quote(ctx_id)}/tasks/{urllib.parse.quote(task_id)}",
        {"status": "in_progress"},
    )
    task = http(
        "PATCH",
        f"/contexts/{urllib.parse.quote(ctx_id)}/tasks/{urllib.parse.quote(task_id)}",
        {"status": "done", "description": task.get("description", "") + " (patched and tested)"},
    )
    print(f"Task updated: status={task['status']}")

    # 7) Record handoff to Kai
    ho = http(
        "POST",
        "/handoffs",
        {
            "from": riley["id"],
            "to": kai["id"],
            "context": ctx_id,
            "task": task_id,
            "summary": "Auth redirect fix is ready; please verify on staging.",
            "next_steps": "Deploy to staging, run smoke suite, check login/logout",
        },
    )
    print(f"Handoff recorded: {ho['id']} -> to={ho['to_agent']}")

    # 8) Teammate fetches latest memories for quick context
    recent = http("GET", f"/contexts/{urllib.parse.quote(ctx_id)}/memories?q=auth")
    print(f"Recent auth memories: {len(recent)} items")

    # Summary
    print("\nSummary")
    print("- Agent Riley:", riley["id"])  # type: ignore[index]
    print("- Agent Kai:", kai["id"])      # type: ignore[index]
    print("- Context:", ctx_id)
    print("- Task:", task_id)
    print("- Memory:", mem["id"])        # type: ignore[index]
    print("- Handoff:", ho["id"])        # type: ignore[index]

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

