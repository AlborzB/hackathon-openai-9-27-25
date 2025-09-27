import { Agent, ContextPool, Event, Handoff, MemoryItem, OrchestrationRun, Task } from './types'

const DEFAULT_BASE_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_BROKER_URL) ||
  (typeof window !== 'undefined' ? window.localStorage.getItem('BROKER_URL') : null) ||
  'http://localhost:7070'

export interface ListContextEventsParams {
  agent_id?: string
  type?: string
  category?: string
  tag?: string
  limit?: number
  after?: string
}

export interface CreateOrchestrationPayload {
  context_id: string
  prompt: string
  policy?: Record<string, unknown>
  created_by?: string
}

export class BrokerHttpClient {
  constructor(private readonly baseUrl: string = DEFAULT_BASE_URL) {}

  private buildUrl(path: string, params?: Record<string, string | number | undefined>): string {
    const url = new URL(path, this.baseUrl)
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        if (value === undefined || value === null || value === '') continue
        url.searchParams.append(key, String(value))
      }
    }
    return url.toString()
  }

  private async request<T>(path: string, init?: RequestInit & { query?: Record<string, unknown> }): Promise<T> {
    const url = this.buildUrl(path, init?.query as Record<string, string | number | undefined> | undefined)
    const res = await fetch(url, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(init?.headers || {}),
      },
    })
    if (!res.ok) {
      let message = `${res.status} ${res.statusText}`
      try {
        const payload = await res.json()
        if (payload?.detail) message = payload.detail
      } catch (err) {
        // ignore JSON parse errors
      }
      throw new Error(`Request failed: ${message}`)
    }
    if (res.status === 204) return undefined as T
    return (await res.json()) as T
  }

  // Agents
  listAgents() {
    return this.request<Agent[]>('/agents')
  }

  // Contexts
  listContexts() {
    return this.request<ContextPool[]>('/contexts')
  }

  // Memories
  listMemories(contextId: string, q?: string) {
    return this.request<MemoryItem[]>(`/contexts/${encodeURIComponent(contextId)}/memories`, {
      query: q ? { q } : undefined,
    })
  }

  // Tasks
  listTasks(contextId: string) {
    return this.request<Task[]>(`/contexts/${encodeURIComponent(contextId)}/tasks`)
  }

  // Handoffs
  listHandoffs(contextId: string) {
    return this.request<Handoff[]>(`/contexts/${encodeURIComponent(contextId)}/handoffs`)
  }

  // Events
  listContextEvents(contextId: string, params?: ListContextEventsParams) {
    return this.request<Event[]>(`/contexts/${encodeURIComponent(contextId)}/events`, {
      query: params as Record<string, unknown> | undefined,
    })
  }

  listRunEvents(runId: string, params?: ListContextEventsParams) {
    return this.request<Event[]>(`/orchestrations/${encodeURIComponent(runId)}/events`, {
      query: params as Record<string, unknown> | undefined,
    })
  }

  // Orchestrations
  createOrchestration(payload: CreateOrchestrationPayload) {
    return this.request<OrchestrationRun>('/orchestrations', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  getOrchestration(runId: string) {
    return this.request<OrchestrationRun>(`/orchestrations/${encodeURIComponent(runId)}`)
  }

  cancelOrchestration(runId: string) {
    return this.request<OrchestrationRun>(`/orchestrations/${encodeURIComponent(runId)}/cancel`, {
      method: 'POST',
    })
  }
}

export const brokerClient = new BrokerHttpClient()

