Examples

This folder contains runnable scenarios that exercise the Agent Memory Broker end‑to‑end. Each example assumes the broker is running locally.

Quick start
- Start the broker: `uvicorn memory_broker.main:app --reload --port 7070`
- Run an example, e.g.: `python examples/multi_agent_handoff/run.py`

Scenarios
- multi_agent_handoff: Simulates two developers collaborating through the broker by creating agents, a context, a task, memories, and a handoff.

