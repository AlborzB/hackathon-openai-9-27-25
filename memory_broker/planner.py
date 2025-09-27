from __future__ import annotations

import os
from typing import Protocol, List
import json
import shlex
import subprocess
from dataclasses import dataclass

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
    if kind == "codex":
        return CodexPlanner.from_env()
    return MockPlanner()


@dataclass
class CodexPlanner:
    """Planner that shells out to Codex CLI (or a compatible command) to get a deterministic PlanV1.

    Security/ops:
    - Does not read or log credentials; relies on Codex CLI auth configured on the host.
    - Command is provided via env var and can be tailored per environment.
    """

    command: List[str]
    timeout_secs: int = 60

    @staticmethod
    def from_env() -> "CodexPlanner":
        cmd_str = os.getenv("BROKER_PLANNER_COMMAND")
        if not cmd_str:
            # Provide a conservative default that many installations can adapt;
            # strongly recommend overriding via BROKER_PLANNER_COMMAND.
            # This default assumes a `codex` CLI that reads prompt from stdin and writes response to stdout.
            cmd_str = "codex chat --model o4-mini"
        cmd = shlex.split(cmd_str)
        t = int(os.getenv("BROKER_PLANNER_TIMEOUT", "60"))
        return CodexPlanner(command=cmd, timeout_secs=t)

    def plan(self, *, context_id: str, prompt: str) -> PlanV1:
        planning_prompt = self._build_prompt(context_id=context_id, user_prompt=prompt)
        proc = subprocess.run(
            self.command,
            input=planning_prompt,
            capture_output=True,
            text=True,
            timeout=self.timeout_secs,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"planner process failed (exit {proc.returncode})")
        stdout = proc.stdout or ""
        plan_obj = self._extract_json(stdout)
        # Validate strict schema
        return PlanV1.model_validate(plan_obj)

    def _build_prompt(self, *, context_id: str, user_prompt: str) -> str:
        # Minimal, deterministic instruction set. The CLI should return ONLY JSON.
        return (
            "You are a planner for a multi-agent system.\n"
            "Given the user's prompt and a context_id, respond with a strictly valid JSON object conforming to PlanV1.\n"
            "Do not include any commentary or markdown, only JSON.\n"
            "Schema summary (PlanV1 v1):\n"
            "{\n"
            "  \"version\": \"1\",\n"
            "  \"agents\": [{ \"name\": string, \"role\"?: string, \"kind\": \"agent\"|\"human\", \"metadata\"?: object }],\n"
            "  \"actions\": [\n"
            "    { \"type\": \"create_agent\", \"spec\": { \"name\": string, \"kind\": \"agent\"|\"human\" }},\n"
            "    { \"type\": \"message\", \"agent_id\": string, \"content\": string },\n"
            "    { \"type\": \"task.create\", \"context_id\": string, \"payload\": { \"title\": string, \"assignee\"?: string, \"tags\"?: [string] }},\n"
            "    { \"type\": \"handoff\", \"payload\": { \"from\": string, \"to\": string, \"context\": string, \"task\": string, \"summary\": string }},\n"
            "    { \"type\": \"subprocess.run\", \"command\": [string], \"env\"?: { [k: string]: string }, \"cwd\"?: string }\n"
            "  ]\n"
            "}\n"
            f"context_id: {context_id}\n"
            f"user_prompt: {user_prompt}\n"
            "Output strictly the JSON object."
        )

    def _extract_json(self, text: str) -> dict:
        # Try direct parse
        try:
            return json.loads(text)
        except Exception:
            pass
        # Look for fenced code blocks
        start = text.find("```")
        while start != -1:
            end = text.find("```", start + 3)
            if end == -1:
                break
            block = text[start + 3 : end]
            # remove possible language hint
            if block.startswith("json\n"):
                block = block[5:]
            try:
                return json.loads(block)
            except Exception:
                start = text.find("```", end + 3)
                continue
        # Last resort: extract first balanced JSON object
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            candidate = text[first : last + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass
        raise ValueError("could not parse planner output as JSON PlanV1")
