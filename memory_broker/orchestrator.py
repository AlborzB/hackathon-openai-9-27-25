from __future__ import annotations

import os
import subprocess
import time
from typing import Optional

from .models import (
    AgentCreate,
    EventCreate,
    HandoffCreate,
    OrchestrationRun,
    PlanV1,
    TaskCreate,
)
from .store.base import MemoryStore
from .planner import get_planner


def execute_run(store: MemoryStore, run: OrchestrationRun, plan: PlanV1) -> None:
    """Execute a deterministic plan for a run. Emits orchestration and domain events.

    Minimal stub that simulates subprocess actions and maps actions to store ops.
    """
    # Transition to running
    store.update_orchestration_status(run.id, "running")
    store.append_event(
        EventCreate(
            context_id=run.context_id,
            run_id=run.id,
            category="orchestration",
            type="run_started",
            actor="broker",
            message="orchestration_started",
        )
    )

    try:
        # Ensure any declared agents are upserted first (pre-flight convenience)
        for spec in plan.agents or []:
            store.append_event(
                EventCreate(
                    context_id=run.context_id,
                    run_id=run.id,
                    category="orchestration",
                    type="action_start",
                    actor="broker",
                    message="create_agent(preflight)",
                    data={"name": spec.name},
                )
            )
            agent = store.upsert_agent(AgentCreate(name=spec.name, kind=spec.kind, metadata=spec.metadata))
            store.append_event(
                EventCreate(
                    context_id=run.context_id,
                    run_id=run.id,
                    category="agent",
                    type="agent_created",
                    actor="broker",
                    agent_id=agent.id,
                    data={"agent_id": agent.id, "name": agent.name},
                )
            )
            store.append_event(
                EventCreate(
                    context_id=run.context_id,
                    run_id=run.id,
                    category="orchestration",
                    type="action_end",
                    actor="broker",
                    message="create_agent(preflight)",
                    data={"name": spec.name},
                )
            )

        # Execute actions in order
        sp_index = 0  # index for subprocess actions to create unique log filenames
        for action in plan.actions:
            # Check for cancellation before each action
            try:
                if store.get_orchestration(run.id).status == "canceled":
                    break
            except Exception:
                # If the run cannot be fetched, abort gracefully
                break
            store.append_event(
                EventCreate(
                    context_id=run.context_id,
                    run_id=run.id,
                    category="orchestration",
                    type="action_start",
                    actor="broker",
                    data={"action_type": getattr(action, "type", "unknown")},
                )
            )

            if action.type == "create_agent":
                spec = action.spec
                agent = store.upsert_agent(AgentCreate(name=spec.name, kind=spec.kind, metadata=spec.metadata))
                store.append_event(
                    EventCreate(
                        context_id=run.context_id,
                        run_id=run.id,
                        category="agent",
                        type="agent_created",
                        actor="broker",
                        agent_id=agent.id,
                        data={"agent_id": agent.id, "name": agent.name},
                    )
                )
            elif action.type == "message":
                store.append_event(
                    EventCreate(
                        context_id=run.context_id,
                        run_id=run.id,
                        category="agent",
                        type="agent_message",
                        actor="agent",
                        agent_id=action.agent_id,
                        message=action.content,
                        data={"agent_id": action.agent_id},
                    )
                )
            elif action.type == "task.create":
                payload: TaskCreate = action.payload
                task = store.add_task(action.context_id, payload)
                # emit domain event for task create
                store.append_event(
                    EventCreate(
                        context_id=task.context_id,
                        run_id=run.id,
                        category="task",
                        type="task_created",
                        actor="broker",
                        agent_id=task.assignee,
                        tags=task.tags or [],
                        data={"task_id": task.id, "title": task.title},
                    )
                )
            elif action.type == "handoff":
                payload: HandoffCreate = action.payload
                handoff = store.record_handoff(payload)
                store.append_event(
                    EventCreate(
                        context_id=handoff.context_id,
                        run_id=run.id,
                        category="handoff",
                        type="handoff_recorded",
                        actor="broker",
                        agent_id=handoff.to_agent,
                        task_id=handoff.task_id,
                        data={"handoff_id": handoff.id, "from": handoff.from_agent, "to": handoff.to_agent},
                    )
                )
            elif action.type == "subprocess.run":
                # Execute external command with optional env and cwd; capture stdout/err to files under logs/runs/<run_id>
                # Safety: do not log environment values; write streams to files and reference their paths in events.
                run_logs_dir = os.path.join("logs", "runs", run.id)
                os.makedirs(run_logs_dir, exist_ok=True)
                # Default working directory per run if not provided
                default_cwd = os.path.join("runs", run.id)
                os.makedirs(default_cwd, exist_ok=True)
                base = f"subprocess_{sp_index:03d}"
                sp_index += 1
                stdout_path = os.path.join(run_logs_dir, f"{base}.stdout.txt")
                stderr_path = os.path.join(run_logs_dir, f"{base}.stderr.txt")

                store.append_event(
                    EventCreate(
                        context_id=run.context_id,
                        run_id=run.id,
                        category="orchestration",
                        type="subprocess_started",
                        actor="broker",
                        data={"command": action.command, "cwd": action.cwd},
                    )
                )

                # Prepare env and timeout
                env = os.environ.copy()
                try:
                    # Only merge if provided and is a dict of strings
                    if getattr(action, "env", None):
                        env.update({str(k): str(v) for k, v in action.env.items()})
                except Exception:
                    # Ignore malformed env
                    pass
                # Inject minimal, safe broker context into environment
                env.setdefault("BROKER_RUN_ID", run.id)
                env.setdefault("BROKER_CONTEXT_ID", run.context_id)
                timeout_s = float(os.getenv("BROKER_SUBPROCESS_TIMEOUT", "120"))

                started = time.monotonic()
                returncode: Optional[int]
                timed_out = False
                try:
                    proc = subprocess.run(  # nosec B603
                        action.command,
                        cwd=action.cwd or default_cwd,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=timeout_s,
                        check=False,
                    )
                    returncode = proc.returncode
                    # Write outputs to files
                    try:
                        with open(stdout_path, "w", encoding="utf-8") as f_out:
                            f_out.write(proc.stdout or "")
                    except Exception:
                        pass
                    try:
                        with open(stderr_path, "w", encoding="utf-8") as f_err:
                            f_err.write(proc.stderr or "")
                    except Exception:
                        pass
                except subprocess.TimeoutExpired as te:  # pragma: no cover - edge
                    timed_out = True
                    returncode = None
                    # Best effort: write partial output if available
                    try:
                        with open(stdout_path, "w", encoding="utf-8") as f_out:
                            if te.stdout:
                                f_out.write(te.stdout)
                    except Exception:
                        pass
                    try:
                        with open(stderr_path, "w", encoding="utf-8") as f_err:
                            if te.stderr:
                                f_err.write(te.stderr)
                    except Exception:
                        pass

                duration_ms = int((time.monotonic() - started) * 1000)

                store.append_event(
                    EventCreate(
                        context_id=run.context_id,
                        run_id=run.id,
                        category="orchestration",
                        type="subprocess_completed",
                        actor="broker",
                        data={
                            "command": action.command,
                            "cwd": action.cwd,
                            "returncode": returncode,
                            "timed_out": timed_out,
                            "duration_ms": duration_ms,
                            "stdout_log": stdout_path,
                            "stderr_log": stderr_path,
                        },
                    )
                )

                # If the subprocess failed or timed out, mark run failed and abort further actions
                if timed_out or (returncode is not None and returncode != 0):
                    raise RuntimeError(
                        f"subprocess failed: rc={returncode} timed_out={timed_out} cmd={' '.join(action.command)}"
                    )
            else:  # pragma: no cover - defensive
                raise ValueError(f"unsupported action type: {getattr(action, 'type', 'unknown')}")

            store.append_event(
                EventCreate(
                    context_id=run.context_id,
                    run_id=run.id,
                    category="orchestration",
                    type="action_end",
                    actor="broker",
                    data={"action_type": getattr(action, "type", "unknown")},
                )
            )

        # Completed
        store.update_orchestration_status(run.id, "completed")
        store.append_event(
            EventCreate(
                context_id=run.context_id,
                run_id=run.id,
                category="orchestration",
                type="run_completed",
                actor="broker",
            )
        )
    except Exception as e:  # pragma: no cover - edge
        store.update_orchestration_status(run.id, "failed")
        store.append_event(
            EventCreate(
                context_id=run.context_id,
                run_id=run.id,
                category="orchestration",
                type="run_failed",
                actor="broker",
                message=str(e),
            )
        )


def plan_and_execute_run(store: MemoryStore, run: OrchestrationRun) -> None:
    """Obtain a plan (via configured planner) and execute it for the run.

    Intended to be invoked on a background task when the run is created without
    an inline plan in the request.
    """
    # Obtain plan
    try:
        planner = get_planner()
        plan = planner.plan(context_id=run.context_id, prompt=run.prompt)

        # Emit plan-ready event (distinct from initial planning_started)
        store.append_event(
            EventCreate(
                context_id=run.context_id,
                run_id=run.id,
                category="plan",
                type="plan_ready",
                actor="broker",
                message="deterministic_plan_ready",
                data={"actions": [getattr(a, "type", "?") for a in plan.actions]},
            )
        )

        # Execute
        execute_run(store, run, plan)
    except Exception as e:  # pragma: no cover
        store.update_orchestration_status(run.id, "failed")
        store.append_event(
            EventCreate(
                context_id=run.context_id,
                run_id=run.id,
                category="orchestration",
                type="run_failed",
                actor="broker",
                message=str(e),
            )
        )
