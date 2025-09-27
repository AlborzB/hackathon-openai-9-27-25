Multi‑Agent Handoff Example

This example drives the Memory Broker via HTTP to simulate a small handoff between two developers.

Run
- Start the API: `uvicorn memory_broker.main:app --reload --port 7070`
- Execute the script: `python examples/multi_agent_handoff/run.py`

What it does
- Upserts two agents (Riley, Kai)
- Creates a context `alpha-sprint`
- Links a GitHub repo to that context
- Creates a task and appends a memory update
- Updates the task status to review
- Records a handoff from Riley to Kai and prints a summary

Configuration
- `BASE_URL` env var (default `http://localhost:7070`)

