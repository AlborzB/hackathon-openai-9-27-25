# Frontend Contracts

## Overview
- The browser UI consumes the Memory Broker over HTTP.
- UI drives orchestration via POST `/orchestrations` and renders the audit trail by polling GET events endpoints with cursors.
- This document defines payload shapes, event→UI mappings, and polling guidance.

## Key Endpoints
- Create run: `POST /orchestrations` (optionally include `plan` for dev inline execution)
- Run status: `GET /orchestrations/{run_id}`
- Run events: `GET /orchestrations/{run_id}/events?after={event_id}&limit=50`
- Context events: `GET /contexts/{context_id}/events?after={event_id}&limit=50`
- Cancel run: `POST /orchestrations/{run_id}/cancel`

See `openapi.yaml` for full schemas and query params.

## Event Model (common fields)
All events share this shape (additional fields optional):

```json
{
  "id": "evt_ab12cd34",
  "context_id": "ctx-...",
  "run_id": "run_...",          // may be null for context-only events
  "category": "orchestration",   // user|plan|orchestration|agent|task|handoff|memory|repo|broker|system
  "type": "run_started",         // fine-grained type
  "actor": "broker",             // user|broker|agent
  "message": "...",              // optional human text
  "tags": ["..."],                // optional
  "agent_id": "frontend",        // optional
  "task_id": "task_...",         // optional
  "handoff_id": "handoff_...",   // optional
  "repo": {                        // optional
    "provider": "github",
    "owner": "o",
    "name": "n",
    "branch": "main"
  },
  "data": { "...": "..." },     // type-specific structured data
  "created_at": "2025-09-27T17:00:00Z"
}
```

## Event Types (examples)
- user_message
```json
{ "category": "user", "type": "user_message", "actor": "user", "message": "Build X" }
```
- plan, plan_ready
```json
{ "category": "plan", "type": "plan", "actor": "broker", "message": "planning_started" }
{ "category": "plan", "type": "plan_ready", "actor": "broker", "data": { "actions": ["create_agent","task.create"] } }
```
- run_started, run_completed, run_failed, run_canceled
```json
{ "category": "orchestration", "type": "run_started", "actor": "broker" }
{ "category": "orchestration", "type": "run_completed", "actor": "broker" }
{ "category": "orchestration", "type": "run_failed", "actor": "broker", "message": "error" }
{ "category": "orchestration", "type": "run_canceled", "actor": "broker" }
```
- action_start, action_end
```json
{ "category": "orchestration", "type": "action_start", "actor": "broker", "data": { "action_type": "task.create" } }
{ "category": "orchestration", "type": "action_end",   "actor": "broker", "data": { "action_type": "task.create" } }
```
- agent_created, agent_message
```json
{ "category": "agent", "type": "agent_created", "actor": "broker", "agent_id": "frontend", "data": { "agent_id": "frontend", "name": "Frontend" } }
{ "category": "agent", "type": "agent_message", "actor": "agent",  "agent_id": "frontend", "message": "hello" }
```
- task_created, task_updated
```json
{ "category": "task", "type": "task_created", "actor": "broker", "task_id": "task_...", "agent_id": "assignee", "data": { "task_id": "task_...", "title": "Implement API" } }
{ "category": "task", "type": "task_updated", "actor": "broker", "task_id": "task_...", "agent_id": "assignee" }
```
- handoff_recorded
```json
{ "category": "handoff", "type": "handoff_recorded", "actor": "broker", "handoff_id": "handoff_...", "task_id": "task_...", "agent_id": "to_agent", "data": { "from": "A", "to": "B" } }
```
- memory_added
```json
{ "category": "memory", "type": "memory_added", "actor": "broker", "message": "...", "tags": ["plan"] }
```
- repo_linked
```json
{ "category": "repo", "type": "repo_linked", "actor": "broker", "repo": { "provider": "github", "owner": "o", "name": "n", "branch": "main" }, "data": { "provider": "github", "owner": "o", "name": "n", "branch": "main" } }
```
- subprocess_started, subprocess_completed (stubbed)
```json
{ "category": "orchestration", "type": "subprocess_started",  "actor": "broker", "data": { "command": ["echo","ok"], "cwd": "." } }
{ "category": "orchestration", "type": "subprocess_completed","actor": "broker", "data": { "command": ["echo","ok"], "cwd": ".", "returncode": 0 } }
```

## UI Mapping (type → category and hints)
- decision/progress
  - user_message → user
  - plan, plan_ready → plan
  - run_started/run_completed/run_failed/run_canceled → orchestration
  - action_start/action_end → orchestration
- agents
  - agent_created, agent_message → agent
- work items
  - task_created/task_updated → task
  - handoff_recorded → handoff
  - memory_added → memory
  - repo_linked → repo
- Icon hints: user (person), plan (flowchart), orchestration (play/flag), agent (robot), task (checklist), handoff (handoff/arrow-right), memory (note), repo (repo/git).

## Polling Guidance
- Use `GET /orchestrations/{run_id}/events?after={last_id}&limit=50` (or context events for context views).
- Start with `limit=50`. If the UI is busy, increase to 100.
- Poll every 1s while a run is active; back off to 3s when idle.
- Empty array means no new events; reuse the previous `after` cursor.
- Always maintain a local `last_id` cursor from the last event in the prior response.

## Run Lifecycle (expected sequences)
- On create (no inline plan): user_message → plan → plan_ready → run_started → …action_start/end… → run_completed | run_failed
- On create (inline plan): user_message → plan → run_started → …action_start/end… → run_completed | run_failed
- On cancel: a `run_canceled` event is appended and status becomes `canceled`. UI should stop polling after showing canceled state.

## Orchestration Requests
- Create without plan (background planning):
```json
POST /orchestrations
{ "context_id": "ctx-...", "prompt": "Build an API" }
```
- Create with plan (dev/testing):
```json
POST /orchestrations
{ "context_id": "ctx-...", "prompt": "Build an API", "plan": { "version": "1", "agents": [{"name": "pm"}], "actions": [] } }
```
- Cancel run:
```json
POST /orchestrations/{run_id}/cancel
```

## Notes
- Event ordering is stable (created_at, then id). Use cursors for pagination.
- Planner is mocked by default; Codex‑backed planner can be enabled later via env without changing the UI.

