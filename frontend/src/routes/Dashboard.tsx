import React, { useEffect, useState } from 'react'
import { EventList } from '../components/feed/EventList'
import { ChatInput } from '../components/chat/ChatInput'
import { FeedEvent } from '../lib/api/types'
import { mockBroker } from '../lib/api/mockBackend'
import { feedStore } from '../lib/state/store'

export function Dashboard() {
  const [events, setEvents] = useState<FeedEvent[]>(feedStore.getState())

  useEffect(() => {
    const unsub = feedStore.subscribe(setEvents)
    // kick off the scenario once when mounted
    feedStore.start(mockBroker)
    return () => unsub()
  }, [])

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', height: '100vh' }}>
      <header style={{ padding: 12, borderBottom: '1px solid #eee' }}>
        <strong>Agent Dashboard</strong>
        <span style={{ marginLeft: 8, color: '#777' }}>payments-rollout</span>
      </header>
      <main style={{ overflowY: 'auto' }}>
        <EventList events={events} />
      </main>
      <footer style={{ padding: 12, borderTop: '1px solid #eee' }}>
        <ChatInput onSend={(evt) => {
          // For now, just append the user prompt to the local feed
          feedStore.appendLocal(evt)
        }} />
      </footer>
    </div>
  )
}
