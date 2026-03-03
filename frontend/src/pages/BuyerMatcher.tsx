
import { useQuery } from '@tanstack/react-query'
import { getMatchDashboard } from '../api'

type Match = { vehicle_id: number; make: string; model: string; list_price_qar: number; match_score: number }
type BuyerRow = { customer: Record<string, unknown>; top_matches: Match[] }

function CircleScore({ score, size = 56 }: { score: number; size?: number }) {
  const r = (size - 8) / 2
  const circ = 2 * Math.PI * r
  const stroke = Math.max(0, (score / 100) * circ)
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="6" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--gold)" strokeWidth="6" strokeDasharray={`${stroke} ${circ}`} strokeLinecap="round" />
    </svg>
  )
}

export default function BuyerMatcher() {
  const { data: rows, isLoading: loading } = useQuery<BuyerRow[]>({
    queryKey: ['match', 'dashboard', 3],
    queryFn: () => getMatchDashboard(3),
  })
  const rowList = rows ?? []

  if (loading && rowList.length === 0) return <div className="card">Loading…</div>

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--gold)', marginBottom: 3 }}>Buyer & Seller Matching Engine</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Customers With Next Upgrade &lt; 90 Days · Top Matches From Inventory</div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {rowList.length === 0 && <div className="card">No ready buyers in the current window.</div>}
        {rowList.map((row: BuyerRow, i: number) => {
          const cust = row.customer as { name?: string; lifetime_value_qar?: number; preferred_body_type?: string; preferred_color?: string; next_upgrade_prediction?: string; nationality?: string }
          const upgrade = cust.next_upgrade_prediction ?? ''
          const isReady = /now|0\s*day|ready/i.test(upgrade)
          const in60 = /\d+\s*day/i.test(upgrade) && parseInt(upgrade, 10) <= 60
          const topMatch = row.top_matches?.[0]
          const matchScore = topMatch?.match_score ?? 0
          const draftMsg = `Hi ${cust.name ?? 'there'}, we have a ${topMatch ? `${topMatch.make} ${topMatch.model}` : 'vehicle'} that matches your preferences. Would you like to schedule a viewing?`
          return (
            <div key={i} className="card" style={{ display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: 18, alignItems: 'center' }}>
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'linear-gradient(135deg, var(--surface2), var(--border))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>👤</div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                  <span style={{ fontSize: 16, fontWeight: 800 }}>{cust.name ?? 'Customer'}</span>
                  {isReady && <span style={{ fontSize: 10, fontWeight: 700, background: 'rgba(34,197,94,0.2)', color: 'var(--green)', padding: '3px 8px', borderRadius: 6 }}>Ready Now</span>}
                  {!isReady && in60 && <span style={{ fontSize: 10, fontWeight: 700, background: 'rgba(245,158,11,0.2)', color: 'var(--gold)', padding: '3px 8px', borderRadius: 6 }}>60 Days</span>}
                </div>
                <div style={{ fontSize: 12, color: 'var(--dim)', marginBottom: 8 }}>Budget ~QAR {(cust.lifetime_value_qar ?? 0).toLocaleString()} · Prefers {cust.preferred_body_type ?? '—'} / {cust.preferred_color ?? '—'} · Upgrade: {upgrade || '—'}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {row.top_matches?.map((m: Match) => (
                    <div key={m.vehicle_id} style={{ padding: '6px 10px', background: 'rgba(255,255,255,0.05)', borderRadius: 8, border: '1px solid var(--border)', fontSize: 12 }}>
                      {m.make} {m.model} — QAR {Number(m.list_price_qar).toLocaleString()} — <strong style={{ color: 'var(--gold)' }}>{m.match_score}%</strong>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircleScore score={matchScore} />
                  <span style={{ position: 'absolute', fontSize: 12, fontWeight: 800 }}>{matchScore}%</span>
                </div>
                <a href={`https://wa.me/?text=${encodeURIComponent(draftMsg)}`} target="_blank" rel="noopener noreferrer" className="btn-outline" style={{ textDecoration: 'none', color: 'var(--green)', borderColor: 'rgba(34,197,94,0.4)' }}>Send WhatsApp</a>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
