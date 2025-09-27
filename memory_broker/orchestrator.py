from __future__ import annotations

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
        for action in plan.actions:
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
                # Stub: simulate a successful subprocess execution without actually running external commands
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
                store.append_event(
                    EventCreate(
                        context_id=run.context_id,
                        run_id=run.id,
                        category="orchestration",
                        type="subprocess_completed",
                        actor="broker",
                        data={"command": action.command, "cwd": action.cwd, "returncode": 0},
                    )
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
