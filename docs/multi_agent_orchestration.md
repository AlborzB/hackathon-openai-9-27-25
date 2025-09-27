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


## Implementation Checklist (Gaps + Tasks)

Use this checklist to drive implementation. Update this document as changes land so the architecture stays current.

- [ ] Models & Store
  - [x] Add `OrchestrationRun` model (id, context_id, prompt, status, policy, created_at).
  - [x] Add `Event` model (id, run_id, context_id, agent_id?, type, message, data, ts, category, actor).
  - [x] In-memory store: collections for runs and events; helpers to append/query events.
  - [ ] JSON persistence (optional, later) for runs/events controlled by `MEMORY_BROKER_STORAGE=json`.

- [ ] API Endpoints (MVP)
  - [x] POST `/orchestrations` to create a run; returns run details.
  - [x] GET `/orchestrations/{id}` to fetch run status/details.
  - [x] GET `/orchestrations/{id}/events` to list run events (supports paging).
  - [x] GET `/contexts/{id}/events` to list context-wide events (supports filters/paging).
  - [x] GET `/contexts/{id}/tasks` to list tasks for Context Detail view.
  - [x] GET `/contexts/{id}/handoffs` to list handoffs for Handoff Center.
  - [x] POST `/orchestrations/{id}/cancel` (optional safety).
  - [x] Update `openapi.yaml` and README with new endpoints.

- [ ] Event Emission (Wire Up Existing Actions)
  - [x] On user prompt (POST /orchestrations): emit `user_message` and `plan` (placeholder) events.
  - [x] On `POST /contexts/{id}/repos`: emit `repo_linked` event.
  - [x] On `POST /contexts/{id}/tasks`: emit `task_created` event.
  - [x] On `PATCH /contexts/{id}/tasks/{task_id}`: emit `task_updated` event.
  - [x] On `POST /handoffs`: emit `handoff_recorded` event.
  - [x] On `POST /contexts/{id}/memories`: emit `memory_appended` event.
  - [x] Standardize `data` payloads (include relevant ids: task_id, memory_id, handoff_id, repo, etc.).

- [ ] Event Schema & Filtering
  - [x] Add `category` computed on the backend for filtering (decision | incident | progress | task | handoff).
  - [x] Add `actor` to identify event origin ("user" | agent_id | "system").
  - [x] Support query params for events endpoints: `?agent_id=&type=&category=&tag=&repo=&limit=&after=` (partial: `agent_id,type,category,tag,limit`).
  - [x] Ensure chronological sort and pagination (cursor by event id implemented; stable ordering).

- [ ] LLM Deterministic Plan Schema (v1)
  - [x] Implement Pydantic models for schema v1 (top-level + actions whitelist).
  - [x] Parser/validator that rejects unknown actions and missing fields.
  - [x] Map actions to store/api operations; emit events before/after each action.
  - [ ] Versioning strategy (`version: "1"`) for forward compatibility.

- [ ] Orchestrator Runner
  - [ ] `orchestrator.py` service to execute runs asynchronously. (Current: synchronous when `plan` provided; background planner+executor added for no-plan runs.)
  - [ ] Spawn Codex CLI subprocess for planning (separate working dir per run).
  - [ ] Spawn per-agent Codex sessions for `run_codex_session` with isolated dirs (`runs/<run>/<agent>/`).
  - [ ] Log subprocess stdout/err to run-scoped files; emit `agent_message` or `command_executed` events.
  - [ ] Respect escalation policy: retries, timeouts, `impasse_after`, `max_attempts_per_step`.
  - [ ] Never read or log credentials; rely on Codex CLI configuration. If needed, pass path via env var without printing.

- [ ] Deduplication & Idempotency
  - [x] Avoid duplicate repo entries on repeated link calls.
  - [ ] Agent upsert remains idempotent by name; document behavior.
  - [ ] Context creation idempotent by normalized name; document behavior.

- [ ] Memories & Search
  - [ ] Extend memories listing to support `?tag=` filter in addition to `q`.
  - [ ] Confirm MemoryItem.refs cover required types (file, url, issue, pr) for UI refs panel.

- [ ] Frontend Contract (Docs)
  - [ ] Document event types → UI categories mapping in README/docs.
  - [ ] Provide example payloads for key events and list endpoints.
  - [ ] Provide recommended polling intervals and pagination usage.
  - [ ] Include run status surface for Top Bar (Running/Blocked/Done).

- [ ] Observability & Delivery
  - [ ] Consider SSE/WebSockets for events (follow-up milestone).
  - [ ] Add basic rate limiting (optional).
  - [ ] Add auth token header support (optional, dev-only for now).

- [ ] Documentation & Maintenance
  - [ ] Keep this doc updated as endpoints/models change.
  - [ ] Update `CONTEXT.md` and `README.md` summaries once MVP endpoints land.
  - [ ] Update `openapi.yaml` snapshot.

## Testing Reference
- See `docs/integration_testing.md` for the integration test plan and current coverage expectations. Keep both documents updated together.
