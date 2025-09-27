Project Context — Agent Memory Broker (Codex CLI Plugin Layer)

Summary
- Purpose: Provide a shared, team-level memory service for multi-agent, multi-repo collaboration, plus an MCP adapter so Codex CLI and other MCP clients can read/write shared context, tasks, and handoffs.
- Stack: FastAPI app with in-memory store; OpenAPI at runtime; optional JSON persistence planned. MCP stdio server wraps the HTTP API as tools.

Code Map
- API service
  - memory_broker/main.py: FastAPI app factory, CORS setup, store injection
  - memory_broker/api.py: Route handlers for agents, contexts, repos, memories, tasks, handoffs
  - memory_broker/models.py: Pydantic models (Agent, ContextPool, MemoryItem, Task, Handoff, request DTOs)
  - memory_broker/store/base.py: MemoryStore interface
  - memory_broker/store/in_memory.py: In-memory implementation (default)
- MCP adapter
  - mcp_broker/server.py: MCP stdio server exposing tools (register_agent, create_context, add_memory, list_memories, add_task, update_task, link_repo, record_handoff)
  - mcp_broker/client.py: HTTP client used by the MCP server
- Tooling and docs
  - scripts/brokerctl.py: Minimal helper CLI to call the HTTP API
  - openapi.yaml: Static OpenAPI snapshot of the HTTP interface
  - README.md: How-to, concepts, API summary, example flows
  - requirements.txt: Runtime deps aligned for MCP + FastAPI

Runtime Requirements
- Python: Prefer system Python 3.11 with sqlite3 support (Codex uses sqlite locally). A 3.12+ interpreter works too if compiled with sqlite3, or via pysqlite3-binary shim.
- Deps (pinned): fastapi==0.115.0, uvicorn==0.32.0, pydantic==2.11.9, httpx==0.27.2, mcp==1.15.0, python-dotenv==1.0.1.

Runbook (HTTP API)
- Install deps: pip install -r requirements.txt
- Start API: uvicorn memory_broker.main:app --port 7070
- Docs: http://localhost:7070/docs (serves OpenAPI)
- Quick smoke (helper CLI):
  - python scripts/brokerctl.py agents add --name "Alice"
  - python scripts/brokerctl.py contexts create --name "hackathon-9-27"
  - python scripts/brokerctl.py memories add --context hackathon-9-27 --author Alice --text "Initial scaffolding done"

Runbook (MCP Adapter)
- Start MCP server: python -m mcp_broker.server --broker-url http://localhost:7070
- Wire Codex CLI (or any MCP client) to the command above over stdio.
- Available tools: register_agent, create_context, add_memory, list_memories, add_task, update_task, link_repo, record_handoff.

Configuration
- Storage backend (future JSON persistence):
  - MEMORY_BROKER_STORAGE=memory (default; in-memory)
  - MEMORY_BROKER_DATA_PATH=./data (planned path for JSON persistence)
- CORS: Permissive for local dev (configured in main.py).

HTTP API (high level)
- Agents: POST /agents, GET /agents
- Contexts: POST /contexts, GET /contexts
- Repos: POST /contexts/{context_id}/repos
- Memories: POST /contexts/{context_id}/memories, GET /contexts/{context_id}/memories?q=...
- Tasks: POST /contexts/{context_id}/tasks, PATCH /contexts/{context_id}/tasks/{task_id}
- Handoffs: POST /handoffs

Git State
- Branch: feature/memory-broker
- Remote: origin → git@github.com:AlborzB/hackathon-openai-9-27-25.git
- Notable commits:
  - Scaffold FastAPI memory broker (models, routes, store, README, openapi, helper)
  - Add MCP adapter (stdio server + HTTP client) and docs
  - Align deps for MCP: uvicorn 0.32.0, pydantic 2.11.9, mcp 1.15.0
  - Resolve README merge conflict preserving local collaboration flow sections

Operational Notes
- Verified the broker boots and serves /openapi.json using a custom Python at /home/rahul/3124/bin/python.
- Resolved dependency resolver conflicts by pinning versions (see requirements.txt).
- If sqlite3 is missing in your interpreter, either rebuild Python with libsqlite3-dev present or use a shim (pysqlite3-binary + sitecustomize.py).

Next Steps (Optional)
- Add JSON file store implementation for persistence behind MEMORY_BROKER_STORAGE=json.
- Add simple auth (token header) for broker endpoints.
- Provide typed client SDKs (Python/TypeScript) for non-MCP consumers.
- Create a PR from feature/memory-broker to main once main exists or set default branch accordingly.

Useful Commands
- Start API: uvicorn memory_broker.main:app --reload --port 7070
- Start MCP: python -m mcp_broker.server --broker-url http://localhost:7070
- Git push (feature): git push -u origin feature/memory-broker
