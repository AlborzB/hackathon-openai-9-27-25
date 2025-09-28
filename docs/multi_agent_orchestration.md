# Multi‑Agent Orchestration Architecture

## Overview
- Goal: Orchestrate multiple autonomous agents to build a full‑stack app from a single user prompt, escalating to the user only on impasses.
- Frontend displays an audit trail sourced from broker events and memories; user prompts the system via UI.
- Planner can invoke a local CLI (Codex/Claude/etc.) to produce a deterministic plan; per‑agent execution sessions are planned as a follow‑up.

## Components
- OrchestrationRun
  - Represents a single run originating from a user prompt.
  - Tracks status and policy (e.g., escalation rules).
- EventLog
  - Append‑only stream of events per run and per context (plan created, agent ensured, task created, command executed, error, escalation, etc.).
- Agents
  - Created on demand (upsert by name). One LLM context per agent via a separate Codex CLI subprocess and per‑agent working dir.
- Orchestrator
  - Executes the planning call (via CLI when configured), validates deterministic JSON output, and performs actions (create agents, agent messages, create tasks, handoffs, subprocess.run). Per‑agent sessions are a planned enhancement.
  - Planner backends:
    - `mock` (default): deterministic local plan suitable for dev/demo.
    - `codex`: shells out to Codex CLI configured on the host to obtain a PlanV1 JSON (no creds are read or logged by the broker).
- Frontend
  - Shows audit trail by calling GET endpoints for runs/events (and memories). Posts prompts that start orchestrations.

## HTTP API (MVP — Implemented)
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
  - `status: Literal["pending","running","completed","failed","canceled"]`
  - `policy: { impasse_after?: int | duration, max_attempts_per_step?: int, require_user_confirmation?: bool }`
  - `created_at: datetime`
- Event
  - `id: str`
  - `run_id: str`
  - `context_id: str`
  - `agent_id?: str`
  - `type: str` — common values include `user_message`, `plan`, `plan_ready`, `run_started`, `action_start`, `action_end`, `agent_created`, `task_created`, `task_updated`, `handoff_recorded`, `memory_added`, `repo_linked`, `subprocess_started`, `subprocess_completed`, `run_completed`, `run_failed`, `run_canceled`.
  - `message: str`
  - `data: dict`
  - `created_at: datetime`

## Deterministic LLM Output Schema (v1)
- Top‑level
  - `version: "1"`
  - `agents: [{ name: string, role?: string, kind?: "agent"|"human", metadata?: object }]`
  - `actions: Action[]`
- Action (whitelist)
  - `{"type": "create_agent", "spec": {"name": "...", "kind": "agent"|"human"}}`
  - `{"type": "message", "agent_id": "...", "content": "..."}`
  - `{"type": "task.create", "context_id": "...", "payload": {"title": "...", "assignee"?: "...", "tags"?: ["..."]}}`
  - `{"type": "handoff", "payload": {"from": "...", "to": "...", "context": "...", "task": "...", "summary": "..."}}`
  - `{"type": "subprocess.run", "command": ["..."], "env"?: {"K": "V"}, "cwd"?: "..."}`
- Validation
  - Parse with Pydantic; reject unknown `type` values or missing fields.
  - Execute actions strictly in order; emit events before/after each action.

## Execution Flow (High Level)
1) UI posts prompt to broker to create an `OrchestrationRun`.
2) Broker persists the run and emits `user_message` and `plan` (planning_started) events.
3) Orchestrator obtains a plan via the configured planner:
   - `mock` returns a deterministic local plan; `codex` shells out to the configured CLI with a strict prompt and expects JSON only.
4) Orchestrator validates the JSON plan against schema v1 and emits `plan_ready`.
5) Orchestrator executes actions in order:
   - Create agents; emit messages; create tasks; record handoffs; run external commands via `subprocess.run` and emit `subprocess_started`/`subprocess_completed` (with logs/return codes). Per‑agent sessions remain a follow‑up.
6) For each action, append `action_start`/`action_end` plus domain events; on errors, retry per policy; escalate if thresholds reached (policy knobs are present but not yet enforced).
7) UI polls run events and displays audit trail; user is prompted only on escalation events (future policy).

## Mermaid Sequence Diagram
```mermaid
sequenceDiagram
    participant UI as Frontend UI
    participant Broker as Memory Broker API
    participant Orch as Orchestrator
    participant LLM as Codex CLI (subprocess)
    participant Store as Store (Agents/Tasks/Memories/Events)

    UI->>Broker: POST /orchestrations {prompt, context_id, policy}
    Broker->>Store: Create OrchestrationRun; append user_message + plan events
    Broker->>Orch: Start run (internal)

    Orch->>LLM: If BROKER_PLANNER=codex, invoke planner CLI
    LLM-->>Orch: Deterministic JSON plan (PlanV1)
    Orch->>Store: Event(plan_ready) with actions summary

    loop For each Action
        Orch->>Store: Event(action_start)
        alt create_agent
            Orch->>Store: Upsert Agent; Event(agent_created)
        else message
            Orch->>Store: Event(agent_message)
        else task.create
            Orch->>Store: Add Task; Event(task_created)
        else handoff
            Orch->>Store: Record Handoff; Event(handoff_recorded)
        else subprocess.run
            Orch->>Store: Event(subprocess_started)
            Orch-->>Store: Event(subprocess_completed)  %% stubbed execution
        end
        Orch->>Store: Event(action_end)
    end

    opt Error or Stall
        Orch->>Store: Event(run_failed)
        Orch->>Store: Event(escalation) with prompt to user  %% future policy
        UI->>Broker: User input only if escalated
    end

    Orch->>Store: Event(run_completed)
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
5) Integrate planner CLI subprocess for planning; follow‑up: per‑agent execution sessions and logging.

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
  - [x] On `POST /contexts/{id}/memories`: emit `memory_added` event.
  - [x] Standardize `data` payloads (include relevant ids: task_id, memory_id, handoff_id, repo, etc.).

- [ ] Event Schema & Filtering
  - [x] Add `category` for filtering (`user|plan|orchestration|agent|task|handoff|memory|repo|broker|system`).
  - [x] Add `actor` to identify event origin ("user" | "broker" | "agent").
  - [x] Support query params for events endpoints: `?agent_id=&type=&category=&tag=&repo=&limit=&after=` (partial: `agent_id,type,category,tag,limit`).
  - [x] Ensure chronological sort and pagination (cursor by event id implemented; stable ordering).

- [ ] LLM Deterministic Plan Schema (v1)
  - [x] Implement Pydantic models for schema v1 (top-level + actions whitelist).
  - [x] Parser/validator that rejects unknown actions and missing fields.
  - [x] Map actions to store/api operations; emit events before/after each action.
  - [x] Versioning strategy: baseline `version: "1"` enforced.

- [ ] Orchestrator Runner
  - [x] Background planning+execution path via FastAPI `BackgroundTasks` (inline plan executes synchronously).
  - [x] Spawn planner CLI subprocess for planning (`BROKER_PLANNER_COMMAND`).
  - [ ] Per‑agent execution sessions with isolated dirs (`runs/<run>/<agent>/`).
  - [ ] Log subprocess stdout/err to run‑scoped files; emit richer execution events.
  - [ ] Respect escalation policy: retries, timeouts, `impasse_after`, `max_attempts_per_step`.
  - [x] Never read or log credentials; rely on Codex/CLI configuration.

- [ ] Deduplication & Idempotency
  - [x] Avoid duplicate repo entries on repeated link calls.
  - [x] Agent upsert idempotent by name (documented in Components).
  - [x] Context creation idempotent by normalized name (e.g., spaces→dashes).

- [ ] Memories & Search
  - [ ] Extend memories listing to support `?tag=` filter in addition to `q`.
  - [x] Confirm `MemoryItem.refs` cover types (file, url, repo, issue, pr).

- [ ] Frontend Contract (Docs)
  - [x] Document event types → UI categories mapping (`docs/frontend_contracts.md`).
  - [x] Provide example payloads for key events and list endpoints.
  - [x] Provide recommended polling intervals and pagination usage.
  - [x] Include run status sequences (see "Run Lifecycle").

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
- See `docs/frontend_contracts.md` for event shapes, UI mappings, and polling guidance.

## Planner Configuration
- Select planner via env: `BROKER_PLANNER=mock|codex` (default: `mock`).
- Codex planner command: set `BROKER_PLANNER_COMMAND` to the full CLI invocation that reads prompt from stdin and returns model output on stdout. Example:
  - `export BROKER_PLANNER=codex`
  - `export BROKER_PLANNER_COMMAND="codex chat --model o4-mini"`
- Planning timeout: `BROKER_PLANNER_TIMEOUT` (seconds, default: 60).
- Input mode:
  - Default is stdin: the broker writes the planning prompt to the CLI's stdin.
  - For CLIs that require a `-p <prompt>` style arg, set:
    - `export BROKER_PLANNER_USE_STDIN=0`
    - `export BROKER_PLANNER_PROMPT_FLAG=-p` (or appropriate flag)
- Security: the broker does not read or log credentials; Codex CLI must be configured separately (e.g., `~/.codex/auth.json`).
