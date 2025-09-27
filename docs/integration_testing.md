# Integration Testing Plan

## Goals
- Validate the Memory Broker end-to-end via HTTP, using a fresh in-memory store per test.
- Exercise all implemented capabilities: agents, contexts, repos, memories, tasks, handoffs, orchestrations, and the events feed.
- Keep tests deterministic, fast, and independent.

## Test Strategy
- In-process HTTP: Use FastAPI `TestClient` against `create_app()` to avoid starting a server.
- Isolation: Create a new app per test function so the in-memory store is clean each time.
- Assertions: Validate HTTP status codes, response schema subsets, idempotency behavior, and emitted events.

## Environment
- Python 3.10+
- Deps from `requirements.txt` (FastAPI + httpx already included). Pytest used for test execution.

## Execution
- Run: `pytest -q`
- Optional: `pytest -q tests/integration/test_*.py -k <keyword>`

## Scope (MVP)
1) Agents & Contexts
   - POST /agents creates or upserts an agent; GET /agents lists it.
   - POST /contexts creates a context; GET /contexts lists it.
2) Memories
   - POST /contexts/{id}/memories creates a memory item.
   - GET /contexts/{id}/memories returns the item; basic `q` filter works.
3) Tasks
   - POST /contexts/{id}/tasks creates a task.
   - PATCH /contexts/{id}/tasks/{task_id} updates the task.
   - GET /contexts/{id}/tasks lists tasks including updates.
4) Handoffs
   - POST /handoffs records a handoff.
   - GET /contexts/{id}/handoffs lists it.
5) Repos
   - POST /contexts/{id}/repos links a repo; duplicate links are deduped by (provider, owner, name, branch).
6) Orchestrations
   - POST /orchestrations creates a run.
   - GET /orchestrations/{run_id} returns details.
7) Events Feed
   - GET /orchestrations/{run_id}/events returns `user_message` + `plan` placeholder after run creation.
   - GET /contexts/{id}/events aggregates events for repo links, memories, task create/update, and handoffs.
   - Filters supported now: `agent_id`, `type`, `category`, `tag`, `limit`.

## Event Expectations (MVP)
- Orchestration creation emits two events in order:
  1) `{ category: "user", type: "user_message" }` with the prompt
  2) `{ category: "plan", type: "plan" }` planning placeholder
- Repo link emits `{ category: "repo", type: "repo_linked" }`.
- Memory add emits `{ category: "memory", type: "memory_added" }`.
- Task create emits `{ category: "task", type: "task_created" }`.
- Task update emits `{ category: "task", type: "task_updated" }`.
- Handoff emits `{ category: "handoff", type: "handoff_recorded" }`.

## Future Coverage (Next Milestones)
- Pagination/cursors for events (`after` cursor, chronological guarantees).
- Orchestrator stub: simulate action execution and verify emitted events sequence.
- Deterministic plan parser: accept/deny plans and validate action whitelist.
- Persistence backend (JSON) integration tests.

## Cross-Reference
- Architecture and checklist live at `docs/multi_agent_orchestration.md`. Update both docs together as features evolve.

