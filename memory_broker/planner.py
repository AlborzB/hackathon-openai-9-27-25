from __future__ import annotations

import os
from typing import Protocol

from .models import PlanV1, AgentSpec, TaskCreateAction, CreateAgentAction, MessageAction


class Planner(Protocol):
    def plan(self, *, context_id: str, prompt: str) -> PlanV1:
        ...


class MockPlanner:
    """A simple deterministic planner used for development/MVP.

    It creates a 'pm' agent, posts an acknowledgement message, and creates a task
    in the provided context based on the prompt title.
    """

    def plan(self, *, context_id: str, prompt: str) -> PlanV1:
        # Derive a concise title from the prompt
        title = prompt.strip().split("\n")[0]
        if len(title) > 80:
            title = title[:77] + "..."

        agents = [AgentSpec(name="pm")]
        actions = [
            CreateAgentAction(spec=AgentSpec(name="pm")),
            MessageAction(agent_id="pm", content=f"Acknowledged prompt: {title}"),
            TaskCreateAction(context_id=context_id, payload={"title": title, "assignee": "pm", "tags": ["auto"]}),
        ]
        return PlanV1(agents=agents, actions=actions)


def get_planner() -> Planner:
    kind = os.getenv("BROKER_PLANNER", "mock").lower().strip()
    # Future: add 'codex' planner that shells out to Codex CLI
    return MockPlanner()

