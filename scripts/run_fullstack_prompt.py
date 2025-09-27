#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import httpx


def _wait_http(url: str, timeout_s: float = 20.0) -> None:
    start = time.time()
    last_err: Optional[str] = None
    while time.time() - start < timeout_s:
        try:
            r = httpx.get(url, timeout=2.0)
            if 200 <= r.status_code < 300:
                return
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            time.sleep(0.3)
    raise RuntimeError(f"server not ready at {url}: {last_err}")


def _start_server(host: str, port: int, reload: bool) -> subprocess.Popen:
    cmd = [sys.executable, "-m", "uvicorn", "memory_broker.main:app", "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")
    env = os.environ.copy()
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)  # noqa: S603
    _wait_http(f"http://{host}:{port}/openapi.json", timeout_s=25.0)
    return proc


def _stop_server(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        try:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:
            pass


def _create_context(client: httpx.Client, name: str) -> str:
    r = client.post("/contexts", json={"name": name})
    r.raise_for_status()
    return r.json()["id"]


def _inline_plan(context_id: str) -> Dict[str, Any]:
    return {
        "version": "1",
        "agents": [
            {"name": "pm"},
            {"name": "architect"},
            {"name": "backend"},
            {"name": "frontend"},
            {"name": "qa"},
        ],
        "actions": [
            {"type": "create_agent", "spec": {"name": "pm"}},
            {"type": "create_agent", "spec": {"name": "architect"}},
            {"type": "create_agent", "spec": {"name": "backend"}},
            {"type": "create_agent", "spec": {"name": "frontend"}},
            {"type": "create_agent", "spec": {"name": "qa"}},
            {"type": "message", "agent_id": "pm", "content": "Kicking off full-stack build"},
            {
                "type": "task.create",
                "context_id": context_id,
                "payload": {"title": "Scaffold backend API", "assignee": "backend", "tags": ["backend", "feat"]},
            },
            {
                "type": "task.create",
                "context_id": context_id,
                "payload": {"title": "Scaffold frontend UI", "assignee": "frontend", "tags": ["frontend", "feat"]},
            },
            {
                "type": "task.create",
                "context_id": context_id,
                "payload": {"title": "Integration tests", "assignee": "qa", "tags": ["qa", "tests"]},
            },
            {"type": "subprocess.run", "command": ["echo", "scaffold"], "cwd": "."},
        ],
    }


def _format_event(e: Dict[str, Any]) -> str:
    parts: List[str] = [e.get("created_at", ""), f"{e.get('category')}.{e.get('type')}"]
    actor = e.get("actor")
    if actor:
        parts.append(f"actor={actor}")
    if e.get("agent_id"):
        parts.append(f"agent={e['agent_id']}")
    if e.get("task_id"):
        parts.append(f"task={e['task_id']}")
    if e.get("handoff_id"):
        parts.append(f"handoff={e['handoff_id']}")
    if e.get("message"):
        parts.append(f"msg={e['message']}")
    return " | ".join(str(p) for p in parts if p)


def run(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Trigger a full-stack app orchestration and stream events")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7070)
    parser.add_argument("--no-server", action="store_true", help="Assume broker is already running")
    parser.add_argument("--reload", action="store_true", help="Start uvicorn with --reload when launching server")
    parser.add_argument("--context-name", default="fullstack-app", help="Context name to create/use")
    parser.add_argument("--prompt", default="Build a full-stack Instagram-like application", help="User prompt")
    parser.add_argument("--inline-plan", action="store_true", help="Send a deterministic inline plan instead of using planner")
    parser.add_argument("--planner", choices=["mock", "codex"], default=None, help="Planner to use when not providing a plan")
    parser.add_argument("--timeout", type=int, default=90, help="Max seconds to wait for completion")
    args = parser.parse_args(argv)

    server_proc: Optional[subprocess.Popen] = None
    try:
        if not args.no_server:
            # Pass planner env to server process if starting it
            if args.planner:
                os.environ["BROKER_PLANNER"] = args.planner
            server_proc = _start_server(args.host, args.port, args.reload)
        else:
            _wait_http(f"http://{args.host}:{args.port}/openapi.json", timeout_s=10.0)

        base_url = f"http://{args.host}:{args.port}"
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            # Create or get context (idempotent by name in this MVP)
            ctx_id = _create_context(client, args.context_name)

            # Build orchestration payload
            body: Dict[str, Any] = {"context_id": ctx_id, "prompt": args.prompt}
            if args.inline_plan:
                body["plan"] = _inline_plan(ctx_id)
            elif args.planner:
                # Planner selection only affects server if we started it; included here for clarity
                pass

            # Create run
            r = client.post("/orchestrations", json=body)
            r.raise_for_status()
            run = r.json()
            run_id = run["id"]
            print(f"Run created: {run_id}")

            after: Optional[str] = None
            start = time.time()
            printed: set[str] = set()
            while time.time() - start < args.timeout:
                # Status
                r = client.get(f"/orchestrations/{run_id}")
                r.raise_for_status()
                status = r.json()["status"]

                # Events
                params = {"limit": 50}
                if after:
                    params["after"] = after
                r = client.get(f"/orchestrations/{run_id}/events", params=params)
                r.raise_for_status()
                events = r.json()
                if events:
                    for e in events:
                        line = _format_event(e)
                        if e["id"] not in printed:
                            print(line)
                            printed.add(e["id"])
                    after = events[-1]["id"]

                if status in ("completed", "failed", "canceled"):
                    print(f"Run finished with status: {status}")
                    return 0 if status == "completed" else 1

                time.sleep(1.0)

            print("Timed out waiting for run to finish")
            return 2

    finally:
        _stop_server(server_proc)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))

