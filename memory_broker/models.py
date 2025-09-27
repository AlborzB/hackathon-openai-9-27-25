from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


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


# Orchestration models

OrchestrationStatus = Literal["pending", "running", "completed", "failed"]


class OrchestrationPolicy(BaseModel):
    # Whether to escalate to user when blocked
    escalate_on_impasse: bool = True
    # Optional caps to keep orchestration bounded
    max_agents: Optional[int] = None
    max_depth: Optional[int] = None
    # Reserved for future policy knobs
    extra: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationRun(BaseModel):
    id: str
    context_id: str
    prompt: str
    created_by: str = "user"
    status: OrchestrationStatus = "pending"
    policy: Optional[OrchestrationPolicy] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


 # NOTE: OrchestrationCreate is defined later to include optional `plan` for tests/local execution


# Event models

EventCategory = Literal[
    "user",
    "system",
    "broker",
    "agent",
    "repo",
    "task",
    "handoff",
    "memory",
    "orchestration",
    "plan",
]

EventActor = Literal["user", "broker", "agent"]


class Event(BaseModel):
    id: str
    context_id: str
    # run_id is optional so we can emit context-level events outside a run
    run_id: Optional[str] = None
    category: EventCategory
    type: str
    actor: EventActor
    message: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    handoff_id: Optional[str] = None
    repo: Optional[RepoRef] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EventCreate(BaseModel):
    context_id: str
    run_id: Optional[str] = None
    category: EventCategory
    type: str
    actor: EventActor
    message: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    handoff_id: Optional[str] = None
    repo: Optional[RepoRef] = None
    data: Dict[str, Any] = Field(default_factory=dict)


# Deterministic Plan schema (v1)

class AgentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    role: Optional[str] = None
    kind: AgentKind = "agent"
    id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateAgentAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["create_agent"] = "create_agent"
    spec: AgentSpec


class MessageAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["message"] = "message"
    agent_id: str
    content: str


class TaskCreateAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["task.create"] = "task.create"
    context_id: str
    payload: TaskCreate


class HandoffAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["handoff"] = "handoff"
    payload: HandoffCreate


class SubprocessRunAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["subprocess.run"] = "subprocess.run"
    command: List[str]
    env: Dict[str, str] = Field(default_factory=dict)
    cwd: Optional[str] = None


PlanAction = Union[
    CreateAgentAction,
    MessageAction,
    TaskCreateAction,
    HandoffAction,
    SubprocessRunAction,
]


class PlanV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["1"] = "1"
    agents: List[AgentSpec] = Field(default_factory=list)
    actions: List[PlanAction] = Field(default_factory=list)


# Extend orchestration create to optionally include a deterministic plan (for tests and local execution)
class OrchestrationCreate(BaseModel):
    context_id: str
    prompt: str
    created_by: str = "user"
    policy: Optional[OrchestrationPolicy] = None
    plan: Optional[PlanV1] = None
