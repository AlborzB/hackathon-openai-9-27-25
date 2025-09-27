Agent Memory Broker (Codex CLI Plugin Layer)

Overview
- Modular memory broker to manage shared, long-term context for multi-agent, multi-repo collaboration.
- Designed to work alongside Codex CLI by exposing a simple HTTP API (OpenAPI-described) so any agent or human can join a shared context pool, append/query memory, and hand off tasks.

Quick Start
1) Python 3.10+
2) Install deps: pip install -r requirements.txt
3) Run server: uvicorn memory_broker.main:app --reload --port 7070
4) Open API docs: http://localhost:7070/docs

Key Concepts
- Agent: A human or automated agent participating in collaboration
- Context Pool: A named workspace shared by a team; associates repos, tasks, and memories
- Memory Item: Structured note/event (who/when/what/refs) stored with tags for recall
- Handoff: Explicit transfer of task ownership between agents with a summary + pointers

HTTP API Summary
- POST /agents: register an agent
- GET /agents: list agents
- POST /contexts: create a context pool
- GET /contexts: list context pools
- POST /contexts/{id}/memories: append memory
- GET /contexts/{id}/memories: list/query memories
- POST /contexts/{id}/repos: link a repo reference
- POST /contexts/{id}/tasks: create task
- PATCH /contexts/{id}/tasks/{task_id}: update task
- POST /handoffs: record a handoff (links agents, task, context)

Storage
- In-memory (default) for hackathon speed
- Optional JSON-file store for lightweight persistence (see MEMORY_BROKER_STORAGE and MEMORY_BROKER_DATA_PATH)

Codex CLI Integration
- Use HTTP calls to read/write shared context during a session.
- Example flows:
  - On start, Codex registers as an Agent and picks/creates a Context Pool for the project.
  - After completing a step, Codex appends a Memory Item with summary, file refs, and links.
  - On task handoff, Codex creates a Handoff record with an actionable next-step summary.

Example: brokerctl (Dev Helper)
- scripts/brokerctl.py offers quick add/list commands against the API for humans.
  - python scripts/brokerctl.py agents add --name "Alice"
  - python scripts/brokerctl.py contexts create --name "hackathon-9-27"
  - python scripts/brokerctl.py memories add --context hackathon-9-27 --author Alice --text "Initial scaffolding done"

Configuration
- MEMORY_BROKER_STORAGE: memory (default) | json
- MEMORY_BROKER_DATA_PATH: path to a folder for JSON persistence (default: ./data)

OpenAPI
- A static OpenAPI document is included at openapi.yaml and served at /openapi.json at runtime.

License
- Hackathon prototype. Use at your own risk.

