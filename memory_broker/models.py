from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


AgentKind = Literal["human", "agent"]


class Agent(BaseModel):
    id: str
    name: str
    kind: AgentKind = "agent"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContextPool(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    repos: List["RepoRef"] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RepoRef(BaseModel):
    provider: Literal["github"] = "github"
    owner: str
    name: str
    branch: Optional[str] = None


class Ref(BaseModel):
    type: Literal["file", "url", "repo", "issue", "pr"]
    value: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class MemoryItem(BaseModel):
    id: str
    context_id: str
    author: str
    text: str
    tags: List[str] = Field(default_factory=list)
    refs: List[Ref] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskStatus(BaseModel):
    value: Literal["todo", "in_progress", "blocked", "done"] = "todo"


class Task(BaseModel):
    id: str
    context_id: str
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    status: Literal["todo", "in_progress", "blocked", "done"] = "todo"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Handoff(BaseModel):
    id: str
    from_agent: str
    to_agent: str
    context_id: str
    task_id: str
    summary: str
    next_steps: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Create/Update models (requests)

class AgentCreate(BaseModel):
    name: str
    kind: AgentKind = "agent"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class MemoryCreate(BaseModel):
    author: str
    text: str
    tags: List[str] = Field(default_factory=list)
    refs: List[Ref] = Field(default_factory=list)


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    status: Literal["todo", "in_progress", "blocked", "done"] = "todo"
    tags: List[str] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[Literal["todo", "in_progress", "blocked", "done"]] = None
    tags: Optional[List[str]] = None


class HandoffCreate(BaseModel):
    from_: str = Field(alias="from")
    to: str
    context: str
    task: str
    summary: str
    next_steps: Optional[str] = None

