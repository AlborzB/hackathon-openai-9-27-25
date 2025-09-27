#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

import httpx


def _get(client: httpx.Client, path: str, **params) -> Any:
    r = client.get(path, params={k: v for k, v in params.items() if v is not None})
    r.raise_for_status()
    return r.json()


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def _fmt_task(t: Dict[str, Any]) -> str:
    return f"{t.get('id')} | {t.get('title')} | assignee={t.get('assignee') or '-'} | status={t.get('status')}"


def _fmt_handoff(h: Dict[str, Any]) -> str:
    task_ref = h.get("task_id") or h.get("task") or "-"
    summary = (h.get("summary") or "").strip().replace("\n", " ")
    if len(summary) > 90:
        summary = summary[:87] + "..."
    return f"{h.get('id')} | to={h.get('to_agent')} | task={task_ref} | {summary}"


def _fmt_event(e: Dict[str, Any]) -> str:
    msg = e.get("message") or ""
    if msg and len(msg) > 80:
        msg = msg[:77] + "..."
    parts: List[str] = [
        e.get("created_at", ""),
        f"{e.get('category')}.{e.get('type')}",
        f"actor={e.get('actor')}",
    ]
    if e.get("agent_id"):
        parts.append(f"agent={e['agent_id']}")
    if e.get("task_id"):
        parts.append(f"task={e['task_id']}")
    if e.get("handoff_id"):
        parts.append(f"handoff={e['handoff_id']}")
    if msg:
        parts.append(f"msg={msg}")
    return " | ".join(parts)


def run(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Verify artifacts for an orchestration run and produce a snapshot")
    p.add_argument("run_id", help="The orchestration run id (e.g., run_ab12cd34)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7070)
    p.add_argument("--limit-events", type=int, default=200, help="Max events to print inline (snapshot always includes all fetched)")
    p.add_argument("--snapshot", default=None, help="Path to write a JSON snapshot (default: run_<id>_snapshot.json)")
    args = p.parse_args(argv)

    base_url = f"http://{args.host}:{args.port}"
    snap_path = args.snapshot or f"run_{args.run_id}_snapshot.json"

    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        # Run details
        run = _get(client, f"/orchestrations/{args.run_id}")
        context_id = run.get("context_id")

        _print_header("Run")
        print(json.dumps({k: run[k] for k in ("id", "context_id", "prompt", "status", "created_at") if k in run}, indent=2))

        # Events (run-scoped)
        events = _get(client, f"/orchestrations/{args.run_id}/events")
        types = sorted(set(e.get("type") for e in events))
        terminal = events[-1]["type"] if events else None

        _print_header("Events (summary)")
        print("unique types:", ", ".join(types))
        print("total:", len(events))
        print("terminal:", terminal)

        _print_header(f"Events (first {min(len(events), args.limit_events)})")
        for e in events[: args.limit_events]:
            print(_fmt_event(e))

        # Context artifacts
        tasks = _get(client, f"/contexts/{context_id}/tasks") if context_id else []
        handoffs = _get(client, f"/contexts/{context_id}/handoffs") if context_id else []
        agents = _get(client, "/agents")

        _print_header("Tasks")
        if tasks:
            for t in tasks:
                print(_fmt_task(t))
        else:
            print("(none)")

        _print_header("Handoffs")
        if handoffs:
            for h in handoffs:
                print(_fmt_handoff(h))
        else:
            print("(none)")

        _print_header("Agents (ids)")
        if agents:
            print(", ".join(sorted(a.get("id") for a in agents if a.get("id"))))
        else:
            print("(none)")

        # Snapshot
        snapshot = {
            "run": run,
            "events": events,
            "tasks": tasks,
            "handoffs": handoffs,
            "agents": agents,
        }
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        _print_header("Snapshot")
        print(f"written: {snap_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())

