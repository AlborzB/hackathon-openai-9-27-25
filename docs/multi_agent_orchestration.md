# Multi‑Agent Orchestration Architecture

## Overview
- Goal: Orchestrate multiple autonomous agents to build a full‑stack app from a single user prompt, escalating to the user only on impasses.
- Frontend displays an audit trail sourced from broker events and memories; user prompts the system via UI.
- Broker invokes Codex CLI as isolated subprocesses to maintain separate LLM contexts per agent.

## Components
- OrchestrationRun
  - Represents a single run originating from a user prompt.
  - Tracks status and policy (e.g., escalation rules).
- EventLog
  - Append‑only stream of events per run and per context (plan created, agent ensured, task created, command executed, error, escalation, etc.).
- Agents
  - Created on demand (upsert by name). One LLM context per agent via a separate Codex CLI subprocess and per‑agent working dir.
- Orchestrator
  - Executes the LLM planning call (Codex CLI subprocess), validates its deterministic JSON output, and performs actions (ensure agents, create tasks, append memories, spawn agent sessions, etc.).
- Frontend
  - Shows audit trail by calling GET endpoints for runs/events (and memories). Posts prompts that start orchestrations.

## Proposed HTTP API Additions (MVP)
- POST `/orchestrations`
  - Start a run with `{ context_id, prompt, policy }` and return `{ id, status, created_at, ... }`.
- GET `/orchestrations/{id}`
  - Get run status/details.
- GET `/orchestrations/{id}/events`
  - List events for the run (UI poll or SSE in a follow‑up).
- GET `/contexts/{id}/events`
  - List context‑wide events (audit trail).
- POST `/orchestrations/{id}/cancel` (optional)
  - Request cancellation for safety.

## Data Models (Pydantic)
- OrchestrationRun
  - `id: str`
  - `context_id: str`
  - `prompt: str`
  - `status: Literal["pending","running","blocked","done","error","canceled"]`
  - `policy: { impasse_after?: int | duration, max_attempts_per_step?: int, require_user_confirmation?: bool }`
  - `created_at: datetime`
- Event
  - `id: str`
  - `run_id: str`
  - `context_id: str`
  - `agent_id?: str`
  - `type: Literal["info","plan","ensure_agents","task_created","memory_appended","command_executed","error","escalation","done"]`
  - `message: str`
  - `data: dict`
  - `ts: datetime`

## Deterministic LLM Output Schema (v1)
- Top‑level
  - `version: "1"`
  - `agents: [{ name: str, role: str, notes?: str }]`
  - `steps: Action[]`
- Action (whitelist)
  - `{"type": "ensure_agents", "agents": [{"name": "backend", "role": "backend_dev"}, ...]}`
  - `{"type": "create_task", "args": {"context_id": "...", "title": "...", "description": "...", "assignee": "backend"}}`
  - `{"type": "append_memory", "args": {"context_id": "...", "author": "pm", "text": "...", "tags": ["plan"]}}`
  - `{"type": "run_codex_session", "args": {"agent": "frontend", "goal": "scaffold UI", "working_dir": "runs/<run_id>/frontend"}}`
- Validation
  - Parse with Pydantic; reject unknown `type` values or missing fields.
  - Execute actions strictly in order; emit events before/after each action.

## Execution Flow (High Level)
1) UI posts prompt to broker to create an `OrchestrationRun`.
2) Broker persists the run and emits a `plan` event.
3) Orchestrator starts a Codex CLI subprocess (separate context) to obtain a deterministic plan.
4) Orchestrator validates the JSON plan against schema v1.
5) Orchestrator executes actions in order:
   - Ensure/create agents; create tasks; append memories; spawn per‑agent Codex sessions with goals and isolated working dirs.
6) For each action, append events; on errors, retry per policy; escalate if thresholds reached.
7) UI polls run events and displays audit trail; only prompts user on broker `escalation` events.

## Mermaid Sequence Diagram
```mermaid
sequenceDiagram
    participant UI as Frontend UI
    participant Broker as Memory Broker API
    participant Orch as Orchestrator
    participant LLM as Codex CLI (subprocess)
    participant Store as Store (Agents/Tasks/Memories/Events)

    UI->>Broker: POST /orchestrations {prompt, context_id, policy}
    Broker->>Store: Create OrchestrationRun; append plan event
    Broker->>Orch: Start run (internal)

    Orch->>LLM: Run Codex CLI with planning prompt
    LLM-->>Orch: Deterministic JSON plan (agents + steps)
    Orch->>Store: Event(plan) with summary

    loop For each Action
        Orch->>Store: Event(info) action-start
        alt ensure_agents
            Orch->>Store: Upsert Agents; Event(ensure_agents)
        else create_task
            Orch->>Store: Add Task; Event(task_created)
        else append_memory
            Orch->>Store: Add Memory; Event(memory_appended)
        else run_codex_session
            Orch->>LLM: Start agent session (isolated working dir)
            LLM-->>Orch: Outputs/artifacts
            Orch->>Store: Event(command_executed)
        end
        Orch->>Store: Event(info) action-end
    end

    opt Error or Stall
        Orch->>Store: Event(error)
        Orch->>Store: Event(escalation) with prompt to user
        UI->>Broker: User input only if escalated
    end

    Orch->>Store: Event(done)
    Broker-->>UI: GET /orchestrations/{id}/events (audit trail)
```

## Security & Isolation
- Credentials: rely on Codex CLI’s existing local auth configuration (do not read or log secrets). If a path must be specified, pass it via environment variable without printing.
- Isolation: one subprocess per agent with separate working directories under `runs/<run_id>/<agent_name>/`.
- Logging: write subprocess stdout/stderr to run‑scoped log files; emit high‑level events only.

## Escalation Policy (Examples)
- `impasse_after`: consecutive errors or time‑based stall duration before escalation.
- `max_attempts_per_step`: cap retries per action.
- `require_user_confirmation`: require confirmation for sensitive actions (optional).

## MVP Implementation Plan
1) Add models and in‑memory store support for `OrchestrationRun` and `Event`.
2) Add endpoints: create run, get run, list run events, list context events.
3) Implement orchestrator stub that simulates plan execution and appends events (no real CLI yet) for frontend integration.
4) Implement deterministic plan parser and whitelist action executor.
5) Integrate Codex CLI subprocess for planning and `run_codex_session` actions, with isolated working dirs and logging.

## Future Enhancements
- Server‑Sent Events (SSE) or WebSockets for live UI updates.
- JSON persistence backend for runs/events.
- Fine‑grained permissions and API tokens.
- Richer action set (repo ops, PRs, test runners), and agent resource quotas.

