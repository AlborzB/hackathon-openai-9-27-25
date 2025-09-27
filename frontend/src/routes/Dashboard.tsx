import React, { useEffect, useMemo, useState } from 'react'
import { EventList } from '../components/feed/EventList'
import { ChatInput } from '../components/chat/ChatInput'
import { brokerClient } from '../lib/api/client'
import { mockBroker } from '../lib/api/mockBackend'
import { FeedEvent } from '../lib/api/types'
import { feedStore } from '../lib/state/store'

export function Dashboard() {
  const [events, setEvents] = useState<FeedEvent[]>(feedStore.getState())
  const [contextId, setContextId] = useState<string | null>(null)
  const [contextName, setContextName] = useState<string>('Loading…')
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const useMock = useMemo(() => import.meta.env.VITE_USE_MOCK === 'true', [])

  useEffect(() => {
    const unsub = feedStore.subscribe(setEvents)
    let active = true

    if (useMock) {
      setContextId('mock')
      setContextName('Mock Scenario')
      setLoading(false)
      feedStore.startMock(mockBroker)
    } else {
      const init = async () => {
        setLoading(true)
        setError(null)
        try {
          const contexts = await brokerClient.listContexts()
          if (!active) return
          if (!contexts.length) {
            setContextName('No contexts found')
            setContextId(null)
            setLoading(false)
            return
          }
          const ctx = contexts[0]
          setContextId(ctx.id)
          setContextName(ctx.name ?? ctx.id)
          feedStore.startLive(brokerClient, ctx.id)
        } catch (err) {
          if (!active) return
          const message = err instanceof Error ? err.message : 'Failed to load contexts'
          setError(message)
          setContextName('Error')
        } finally {
          if (active) setLoading(false)
        }
      }
      init()
    }

    return () => {
      active = false
      unsub()
      feedStore.stop()
    }
  }, [useMock])

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', height: '100vh' }}>
      <header style={{ padding: 12, borderBottom: '1px solid #eee' }}>
        <strong>Agent Dashboard</strong>
        <span style={{ marginLeft: 8, color: '#777' }}>{contextName}</span>
        {loading && <span style={{ marginLeft: 12, color: '#999' }}>Loading…</span>}
        {error && <span style={{ marginLeft: 12, color: '#d00' }}>{error}</span>}
      </header>
      <main style={{ overflowY: 'auto' }}>
        {events.length === 0 && !loading ? (
          <div style={{ padding: 24, color: '#777' }}>No activity yet.</div>
        ) : (
          <EventList events={events} />
        )}
      </main>
      <footer style={{ padding: 12, borderTop: '1px solid #eee' }}>
        <ChatInput
          onSend={async (text) => {
            if (useMock) {
              feedStore.appendLocal({
                id: `user_${Math.random().toString(16).slice(2, 10)}`,
                ts: Date.now(),
                kind: 'user',
                text,
              })
              return
            }
            if (!contextId) {
              throw new Error('No context available')
            }
            await brokerClient.createOrchestration({ context_id: contextId, prompt: text })
            await feedStore.refresh()
          }}
        />
      </footer>
    </div>
  )
}
