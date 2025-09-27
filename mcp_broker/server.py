from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .client import MemoryBrokerClient


def _schema(properties: Dict[str, Any], required: List[str] | None = None) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def build_server(client: MemoryBrokerClient) -> Server:
    server = Server("memory-broker-mcp")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="register_agent",
                description="Register an agent or human participant",
                inputSchema=_schema({
                    "name": {"type": "string"},
                    "kind": {"type": "string", "enum": ["agent", "human"], "default": "agent"},
                    "metadata": {"type": "object"},
                }, required=["name"]),
            ),
            Tool(
                name="create_context",
                description="Create a shared context pool",
                inputSchema=_schema({
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                }, required=["name"]),
            ),
            Tool(
                name="add_memory",
                description="Append a memory item to a context",
                inputSchema=_schema({
                    "context_id": {"type": "string"},
                    "author": {"type": "string"},
                    "text": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                }, required=["context_id", "author", "text"]),
            ),
            Tool(
                name="list_memories",
                description="List or search memories in a context",
                inputSchema=_schema({
                    "context_id": {"type": "string"},
                    "q": {"type": "string"},
                }, required=["context_id"]),
            ),
            Tool(
                name="add_task",
                description="Create a task in a context",
                inputSchema=_schema({
                    "context_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "assignee": {"type": "string"},
                    "status": {"type": "string", "enum": ["todo", "in_progress", "blocked", "done"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                }, required=["context_id", "title"]),
            ),
            Tool(
                name="update_task",
                description="Update a task in a context",
                inputSchema=_schema({
                    "context_id": {"type": "string"},
                    "task_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "assignee": {"type": "string"},
                    "status": {"type": "string", "enum": ["todo", "in_progress", "blocked", "done"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                }, required=["context_id", "task_id"]),
            ),
            Tool(
                name="link_repo",
                description="Attach a repo reference to a context (e.g., GitHub repo)",
                inputSchema=_schema({
                    "context_id": {"type": "string"},
                    "provider": {"type": "string", "enum": ["github"]},
                    "owner": {"type": "string"},
                    "name": {"type": "string"},
                    "branch": {"type": "string"},
                }, required=["context_id", "provider", "owner", "name"]),
            ),
            Tool(
                name="record_handoff",
                description="Record a task handoff between agents",
                inputSchema=_schema({
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "context": {"type": "string"},
                    "task": {"type": "string"},
                    "summary": {"type": "string"},
                    "next_steps": {"type": "string"},
                }, required=["from", "to", "context", "task", "summary"]),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        try:
            if name == "register_agent":
                res = client.register_agent(
                    name=arguments["name"],
                    kind=arguments.get("kind", "agent"),
                    metadata=arguments.get("metadata") or {},
                )
                return [TextContent(type="text", text=json.dumps(res))]
            if name == "create_context":
                res = client.create_context(
                    name=arguments["name"],
                    description=arguments.get("description"),
                    tags=arguments.get("tags") or [],
                )
                return [TextContent(type="text", text=json.dumps(res))]
            if name == "add_memory":
                res = client.add_memory(
                    context_id=arguments["context_id"],
                    author=arguments["author"],
                    text=arguments["text"],
                    tags=arguments.get("tags") or [],
                )
                return [TextContent(type="text", text=json.dumps(res))]
            if name == "list_memories":
                res = client.list_memories(
                    context_id=arguments["context_id"],
                    q=arguments.get("q"),
                )
                return [TextContent(type="text", text=json.dumps(res))]
            if name == "add_task":
                res = client.add_task(
                    context_id=arguments["context_id"],
                    title=arguments["title"],
                    description=arguments.get("description"),
                    assignee=arguments.get("assignee"),
                    status=arguments.get("status", "todo"),
                    tags=arguments.get("tags") or [],
                )
                return [TextContent(type="text", text=json.dumps(res))]
            if name == "update_task":
                fields = {k: v for k, v in arguments.items() if k not in ("context_id", "task_id") and v is not None}
                res = client.update_task(arguments["context_id"], arguments["task_id"], **fields)
                return [TextContent(type="text", text=json.dumps(res))]
            if name == "link_repo":
                res = client.link_repo(
                    context_id=arguments["context_id"],
                    provider=arguments["provider"],
                    owner=arguments["owner"],
                    name=arguments["name"],
                    branch=arguments.get("branch"),
                )
                return [TextContent(type="text", text=json.dumps(res))]
            if name == "record_handoff":
                res = client.record_handoff(
                    from_agent=arguments["from"],
                    to=arguments["to"],
                    context=arguments["context"],
                    task=arguments["task"],
                    summary=arguments["summary"],
                    next_steps=arguments.get("next_steps"),
                )
                return [TextContent(type="text", text=json.dumps(res))]
        except Exception as e:  # noqa: BLE001
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

        return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]

    return server


async def _amain(broker_url: str) -> None:
    client = MemoryBrokerClient(broker_url)
    server = build_server(client)
    async with stdio_server() as (read, write):
        await server.run(read, write)


def run_server(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="MCP server for Agent Memory Broker")
    parser.add_argument("--broker-url", default="http://localhost:7070")
    args = parser.parse_args(argv)
    asyncio.run(_amain(args.broker_url))


if __name__ == "__main__":
    run_server()

