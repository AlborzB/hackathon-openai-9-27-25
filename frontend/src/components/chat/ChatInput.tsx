import React, { useState } from 'react'

interface Props {
  onSend: (text: string) => Promise<void> | void
}

export function ChatInput({ onSend }: Props) {
  const [text, setText] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const value = text.trim()
    if (!value || pending) return
    setPending(true)
    setError(null)
    try {
      await onSend(value)
      setText('')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send prompt'
      setError(message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8 }}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe what you need…"
          disabled={pending}
          style={{ flex: 1, padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }}
        />
        <button type="submit" disabled={pending || !text.trim()} style={{ padding: '8px 12px' }}>
          {pending ? 'Sending…' : 'Send'}
        </button>
      </form>
      {error && <div style={{ marginTop: 6, color: '#d00', fontSize: 12 }}>{error}</div>}
    </div>
  )
}
