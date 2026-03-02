import { useEffect, useRef, useState } from 'react'
import { chat } from '../api'

const QUICK_QUESTIONS = [
  'What should I buy this month?',
  'Which cars are at risk?',
  'Best time to sell a Prado?',
  'Why aren\'t my red cars not selling?',
]

export default function AIAdvisor() {
  const [message, setMessage] = useState('')
  const [replies, setReplies] = useState<Array<{ user: string; bot: string; sources?: string[] }>>([])
  const [loading, setLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  const send = (text?: string) => {
    const toSend = (text ?? message).trim()
    if (!toSend) return
    setMessage('')
    setReplies((r) => [...r, { user: toSend, bot: '...', sources: undefined }])
    setLoading(true)
    // Prefer SSE streaming endpoint; fall back to non-streaming chat on error.
    try {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      const url = `/api/chat/stream?message=${encodeURIComponent(toSend)}`
      const es = new EventSource(url)
      eventSourceRef.current = es

      setReplies((prev) => {
        const next = [...prev]
        next[next.length - 1] = { ...next[next.length - 1], bot: '', sources: ['INVENTORY', 'SALES', 'ECONOMICS', 'CALENDAR', 'TRENDS'] }
        return next
      })

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as { response?: string; error?: string }
          if (data.error) {
            setReplies((prev) => {
              const next = [...prev]
              next[next.length - 1] = { ...next[next.length - 1], bot: `Error: ${data.error}`, sources: [] }
              return next
            })
            es.close()
            setLoading(false)
            return
          }
          if (data.response) {
            setReplies((prev) => {
              const next = [...prev]
              const last = next[next.length - 1]
              next[next.length - 1] = { ...last, bot: (last.bot ?? '') + data.response }
              return next
            })
          }
        } catch {
          // Ignore malformed chunks
        }
      }

      es.onerror = () => {
        es.close()
        // Fallback to non-streaming chat
        chat(toSend)
          .then((res: { reply: string; sources?: string[] }) => {
            setReplies((prev) => {
              const next = [...prev]
              next[next.length - 1] = {
                ...next[next.length - 1],
                bot: res.reply,
                sources: res.sources ?? ['INVENTORY', 'SALES', 'ECONOMICS', 'CALENDAR', 'TRENDS'],
              }
              return next
            })
          })
          .catch((e) => {
            setReplies((prev) => {
              const next = [...prev]
              next[next.length - 1] = { ...next[next.length - 1], bot: `Error: ${e.message}`, sources: [] }
              return next
            })
          })
          .finally(() => setLoading(false))
      }

      es.onopen = () => {
        // Connection established; keep loading true until stream ends
      }
    } catch (e: any) {
      chat(toSend)
        .then((res: { reply: string; sources?: string[] }) => {
          setReplies((prev) => {
            const next = [...prev]
            next[next.length - 1] = {
              ...next[next.length - 1],
              bot: res.reply,
              sources: res.sources ?? ['INVENTORY', 'SALES', 'ECONOMICS', 'CALENDAR', 'TRENDS'],
            }
            return next
          })
        })
        .catch((err: any) => {
          setReplies((prev) => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], bot: `Error: ${err.message}`, sources: [] }
            return next
          })
        })
        .finally(() => setLoading(false))
    }
  }

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--gold)', marginBottom: 3 }}>AI Advisor Chat</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Ask QAUTO-AI about market, pricing, inventory, or buyers · Data from all datasets</div>
      </div>

      <div className="card" style={{ maxWidth: 640 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {QUICK_QUESTIONS.map((q) => (
            <button key={q} className="pill" onClick={() => send(q)} disabled={loading} style={{ whiteSpace: 'nowrap' }}>
              {q}
            </button>
          ))}
        </div>

        <div style={{ maxHeight: 380, overflow: 'auto', marginBottom: 16 }}>
          {replies.length === 0 && (
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Click a question above or type below. Try: &quot;What should I buy this month?&quot;</div>
          )}
          {replies.map((r, i) => (
            <div key={i} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
                <div style={{ maxWidth: '85%', background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 12, padding: '10px 14px', fontSize: 13 }}>
                  <div style={{ fontSize: 10, color: 'var(--gold)', marginBottom: 4 }}>You</div>
                  {r.user}
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 4 }}>
                <div style={{ maxWidth: '85%', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 12, padding: '10px 14px', fontSize: 13 }}>
                  <div style={{ fontSize: 10, color: 'var(--dim)', marginBottom: 4 }}>QAUTO-AI</div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{r.bot}</div>
                  {r.sources && r.sources.length > 0 && (
                    <div style={{ marginTop: 10, fontSize: 10, color: 'var(--muted)', display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {r.sources.map((s) => (
                        <span key={s} style={{ background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: 4 }}>[{s}]</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder="اكتب سؤالك هنا أو باللغة الإنجليزية..."
            style={{ flex: 1 }}
          />
          <button className="btn-gold" onClick={() => send()} disabled={loading} style={{ padding: '10px 20px' }}>Send</button>
        </div>
      </div>
    </div>
  )
}
