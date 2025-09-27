from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx


class MemoryBrokerClient:
    def __init__(self, base_url: str = "http://localhost:7070", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    # Agents
    def register_agent(self, name: str, kind: str = "agent", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"name": name, "kind": kind, "metadata": metadata or {}}
        r = self._client.post("/agents", json=payload)
        r.raise_for_status()
        return r.json()

    def list_agents(self) -> List[Dict[str, Any]]:
        r = self._client.get("/agents")
        r.raise_for_status()
        return r.json()

    # Contexts
    def create_context(self, name: str, description: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        payload = {"name": name, "description": description, "tags": tags or []}
        r = self._client.post("/contexts", json=payload)
        r.raise_for_status()
        return r.json()

    def list_contexts(self) -> List[Dict[str, Any]]:
        r = self._client.get("/contexts")
        r.raise_for_status()
        return r.json()

    def link_repo(self, context_id: str, provider: str, owner: str, name: str, branch: Optional[str] = None) -> Dict[str, Any]:
        payload = {"provider": provider, "owner": owner, "name": name, "branch": branch}
        r = self._client.post(f"/contexts/{context_id}/repos", json=payload)
        r.raise_for_status()
        return r.json()

    # Memories
    def add_memory(self, context_id: str, author: str, text: str, tags: Optional[List[str]] = None, refs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        payload = {"author": author, "text": text, "tags": tags or [], "refs": refs or []}
        r = self._client.post(f"/contexts/{context_id}/memories", json=payload)
        r.raise_for_status()
        return r.json()

    def list_memories(self, context_id: str, q: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"q": q} if q else None
        r = self._client.get(f"/contexts/{context_id}/memories", params=params)
        r.raise_for_status()
        return r.json()

    # Tasks
    def add_task(self, context_id: str, title: str, description: Optional[str] = None, assignee: Optional[str] = None, status: str = "todo", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        payload = {
            "title": title,
            "description": description,
            "assignee": assignee,
            "status": status,
            "tags": tags or [],
        }
        r = self._client.post(f"/contexts/{context_id}/tasks", json=payload)
        r.raise_for_status()
        return r.json()

    def update_task(self, context_id: str, task_id: str, **fields: Any) -> Dict[str, Any]:
        r = self._client.patch(f"/contexts/{context_id}/tasks/{task_id}", json=fields)
        r.raise_for_status()
        return r.json()

    # Handoffs
    def record_handoff(self, from_agent: str, to: str, context: str, task: str, summary: str, next_steps: Optional[str] = None) -> Dict[str, Any]:
        payload = {"from": from_agent, "to": to, "context": context, "task": task, "summary": summary, "next_steps": next_steps}
        r = self._client.post("/handoffs", json=payload)
        r.raise_for_status()
        return r.json()

