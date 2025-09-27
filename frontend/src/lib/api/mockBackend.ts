import { Agent, ContextPool, Handoff, MemoryItem, Notification, RepoRef, Task } from './types'

// Simple in-memory mock broker with a scripted sequence + subscriptions

type Listener = (n: Notification) => void

export interface BrokerAPI {
  // Queries
  listAgents(): Promise<Agent[]>
  listContexts(): Promise<ContextPool[]>
  listMemories(contextId: string): Promise<MemoryItem[]>
  listTasks(contextId: string): Promise<Task[]>
  listHandoffs(): Promise<Handoff[]>

  // Timeline/notifications
  subscribe(fn: Listener): () => void
  startScenario(): void
  reset(): void
}

// Utilities
const now = () => Date.now()
const id = (p: string) => `${p}_${Math.random().toString(16).slice(2, 10)}`

class MockBroker implements BrokerAPI {
  private agents: Record<string, Agent> = {}
  private contexts: Record<string, ContextPool> = {}
  private memories: Record<string, MemoryItem[]> = {}
  private tasks: Record<string, Record<string, Task>> = {}
  private handoffs: Record<string, Handoff> = {}
  private listeners: Set<Listener> = new Set()
  private timers: number[] = []

  listAgents = async () => Object.values(this.agents)
  listContexts = async () => Object.values(this.contexts)
  listMemories = async (contextId: string) => this.memories[contextId] ?? []
  listTasks = async (contextId: string) => Object.values(this.tasks[contextId] ?? {})
  listHandoffs = async () => Object.values(this.handoffs)

  subscribe = (fn: Listener) => {
    this.listeners.add(fn)
    return () => this.listeners.delete(fn)
  }

  private emit(n: Notification) {
    for (const l of this.listeners) l(n)
  }

  reset() {
    this.agents = {}
    this.contexts = {}
    this.memories = {}
    this.tasks = {}
    this.handoffs = {}
    this.timers.forEach((t) => clearTimeout(t))
    this.timers = []
  }

  startScenario() {
    this.reset()

    const schedule = (ms: number, fn: () => void) => {
      const t = setTimeout(fn, ms) as unknown as number
      this.timers.push(t)
    }

    // 0s: two agents
    schedule(0, () => {
      const riley: Agent = { id: 'riley', name: 'Riley', kind: 'human' }
      const kai: Agent = { id: 'kai', name: 'Kai', kind: 'human' }
      this.agents[riley.id] = riley
      this.agents[kai.id] = kai
      this.emit({ id: id('n'), ts: now(), kind: 'agent_created', payload: riley })
      this.emit({ id: id('n'), ts: now(), kind: 'agent_created', payload: kai })
    })

    // 1s: context + repos
    schedule(1000, () => {
      const ctx: ContextPool = { id: 'payments-rollout', name: 'payments-rollout', tags: ['epic:payments'] }
      this.contexts[ctx.id] = ctx
      this.memories[ctx.id] = []
      this.tasks[ctx.id] = {}
      this.emit({ id: id('n'), ts: now(), kind: 'context_created', payload: ctx })

      const repoApi: RepoRef = { provider: 'github', owner: 'org', name: 'api', branch: 'main' }
      const repoWeb: RepoRef = { provider: 'github', owner: 'org', name: 'web', branch: 'main' }
      ctx.repos = [repoApi, repoWeb]
      this.emit({ id: id('n'), ts: now(), kind: 'repo_linked', payload: { context_id: ctx.id, repo: repoApi } })
      this.emit({ id: id('n'), ts: now(), kind: 'repo_linked', payload: { context_id: ctx.id, repo: repoWeb } })
    })

    // 2s: create task
    schedule(2000, () => {
      const task: Task = {
        id: id('task'),
        context_id: 'payments-rollout',
        title: 'Enable JWT in API',
        description: 'Introduce HS256 behind feature flag',
        assignee: 'riley',
        status: 'todo',
        tags: ['repo:api', 'topic:auth'],
      }
      this.tasks[task.context_id][task.id] = task
      this.emit({ id: id('n'), ts: now(), kind: 'task_created', payload: task })
    })

    // 3s: progress memory with PR ref
    schedule(3000, () => {
      const mem: MemoryItem = {
        id: id('mem'),
        context_id: 'payments-rollout',
        author: 'riley',
        text: 'API JWT feature behind flag; PR #456 open.',
        tags: ['type:progress', 'epic:payments', 'repo:api'],
        refs: [{ type: 'pr', value: 'org/api#456', meta: { status: 'open' } }],
      }
      this.memories[mem.context_id].push(mem)
      this.emit({ id: id('n'), ts: now(), kind: 'memory_added', payload: mem })
    })

    // 4s: task to in_progress
    schedule(4000, () => {
      const ctxId = 'payments-rollout'
      const t = Object.values(this.tasks[ctxId])[0]
      if (!t) return
      t.status = 'in_progress'
      this.emit({ id: id('n'), ts: now(), kind: 'task_updated', payload: { ...t } })
    })

    // 5s: incident memory by SRE
    schedule(5000, () => {
      const mem: MemoryItem = {
        id: id('mem'),
        context_id: 'payments-rollout',
        author: 'kai', // pretending Kai logs this (could be Zo in a richer scenario)
        text: 'INC-134 detected: 401 spike after flag on.',
        tags: ['type:incident', 'sev:2', 'service:auth'],
        refs: [{ type: 'url', value: 'https://runbook/auth-spikes' }],
      }
      this.memories[mem.context_id].push(mem)
      this.emit({ id: id('n'), ts: now(), kind: 'memory_added', payload: mem })
    })

    // 6s: task to done
    schedule(6000, () => {
      const ctxId = 'payments-rollout'
      const t = Object.values(this.tasks[ctxId])[0]
      if (!t) return
      t.status = 'done'
      this.emit({ id: id('n'), ts: now(), kind: 'task_updated', payload: { ...t } })
    })

    // 7s: handoff to Kai
    schedule(7000, () => {
      const ho: Handoff = {
        id: id('handoff'),
        from_agent: 'riley',
        to_agent: 'kai',
        context_id: 'payments-rollout',
        task_id: Object.keys(this.tasks['payments-rollout'])[0],
        summary: 'API JWT feature ready; test flag on staging',
        next_steps: 'Run smoke suite; verify 401/403 paths',
      }
      this.handoffs[ho.id] = ho
      this.emit({ id: id('n'), ts: now(), kind: 'handoff_recorded', payload: ho })
    })
  }
}

export const mockBroker: BrokerAPI = new MockBroker()

