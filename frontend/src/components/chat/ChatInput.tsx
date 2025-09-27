import React, { useState } from 'react'
import { FeedEvent } from '../../lib/api/types'

export function ChatInput({ onSend }: { onSend: (evt: FeedEvent) => void }) {
  const [text, setText] = useState('')
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (!text.trim()) return
        const evt: FeedEvent = {
          id: `user_${Math.random().toString(16).slice(2, 10)}`,
          ts: Date.now(),
          kind: 'user',
          text,
        }
        onSend(evt)
        setText('')
      }}
      style={{ display: 'flex', gap: 8 }}
    >
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type a prompt…"
        style={{ flex: 1, padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }}
      />
      <button type="submit" style={{ padding: '8px 12px' }}>
        Send
      </button>
    </form>
  )
}

