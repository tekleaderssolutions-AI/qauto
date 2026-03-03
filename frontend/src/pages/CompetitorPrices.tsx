import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCompetitors } from '../api'

type Item = {
  make: string
  model: string
  trim: string
  year: number
  color: string
  mileage_km?: number
  price: number
  our_price: number
  gap: number
  gap_pct?: number
  platform: string
  location?: string
  days_listed: number
}

const PLATFORM_COLORS: Record<string, string> = {
  qatarsale: '#f59e0b',
  qatarliving: '#3b82f6',
  facebook: '#1877f2',
  dubizzle: '#22c55e',
  other: '#64748b',
}

function platformColor(p: string) {
  if (!p) return PLATFORM_COLORS.other
  const k = Object.keys(PLATFORM_COLORS).find((x) => String(p).toLowerCase().includes(x))
  return k ? PLATFORM_COLORS[k] : PLATFORM_COLORS.other
}

const MODELS = ['All', 'Land Cruiser', 'Prado', 'Lexus', 'Patrol', 'Hilux', 'Fortuner']
const SORTS = [
  { id: 'gap', label: 'Price Gap' },
  { id: 'price', label: 'Lowest Price' },
  { id: 'days', label: 'Stale First' },
]

export default function CompetitorPrices() {
  const [modelFilter, setModelFilter] = useState('All')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('gap')
  const { data, isLoading: loading } = useQuery({
    queryKey: ['competitors', modelFilter, search, sort],
    queryFn: () => getCompetitors({
      model_filter: modelFilter === 'All' ? undefined : modelFilter,
      search: search || undefined,
      sort,
      limit: 100,
    }),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })
  const items = (data as { items?: Item[] } | undefined)?.items ?? []
  const platformSummary = (data as { platform_summary?: Record<string, { count: number; avg_price: number }> } | undefined)?.platform_summary ?? {}

  const priceAlert = items.some((i) => i.gap > 15000)
  const staleCount = items.filter((i) => (i.days_listed ?? 0) >= 45).length

  const kpis = [
    { label: 'Listings', value: items.length },
    { label: 'Avg Competitor', value: items.length ? Math.round(items.reduce((a, i) => a + i.price, 0) / items.length).toLocaleString() : '—' },
    { label: 'Our Avg', value: items.length ? Math.round(items.reduce((a, i) => a + i.our_price, 0) / items.length).toLocaleString() : '—' },
    { label: 'Avg Gap', value: items.length ? Math.round(items.reduce((a, i) => a + i.gap, 0) / items.length).toLocaleString() : '—' },
    { label: 'Stale (45d+)', value: staleCount },
  ]

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--gold)', marginBottom: 3 }}>Competitor Price Matching</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Compare Our Prices vs Market Listings · Adjust To Win</div>
      </div>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Search model or platform..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: '1 1 200px', maxWidth: 280 }}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          {SORTS.map((s) => (
            <button key={s.id} className={`pill ${sort === s.id ? 'active' : ''}`} onClick={() => setSort(s.id)}>{s.label}</button>
          ))}
        </div>
      </div>

      {priceAlert && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10, padding: '10px 14px', marginBottom: 12, fontSize: 12 }}>
          <strong style={{ color: 'var(--red)' }}>Price alert:</strong> Some listings are QAR 15k+ below our price. Consider dropping to match.
        </div>
      )}
      {staleCount > 0 && (
        <div style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 10, padding: '10px 14px', marginBottom: 12, fontSize: 12 }}>
          <strong style={{ color: 'var(--gold)' }}>Stale opportunity:</strong> {staleCount} competitor listing(s) 45+ days — they may accept lower offers.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginBottom: 16 }}>
        {kpis.map((k, i) => (
          <div key={i} className="kpi-card">
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value" style={{ color: 'var(--gold)' }}>{k.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        {MODELS.map((m) => (
          <button key={m} className={`pill ${modelFilter === m ? 'active' : ''}`} onClick={() => setModelFilter(m)}>{m}</button>
        ))}
      </div>

      {loading ? (
        <div className="card" style={{ textAlign: 'center', color: 'var(--muted)' }}>Loading…</div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14, marginBottom: 18 }}>
            {items.map((row, idx) => (
              <div key={idx} className="card" style={{ borderLeft: `4px solid ${platformColor(row.platform)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: platformColor(row.platform), textTransform: 'uppercase' }}>{row.platform}</span>
                  {row.gap > 0 && row.gap < 20000 && <span style={{ fontSize: 10, background: 'rgba(34,197,94,0.15)', color: 'var(--green)', padding: '2px 8px', borderRadius: 6 }}>#{(idx + 1)} vs us</span>}
                </div>
                <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 6 }}>{row.make} {row.model} {row.trim} {row.year}</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                  <div><span style={{ color: 'var(--muted)' }}>Their price</span><br /><strong>QAR {Number(row.price).toLocaleString()}</strong></div>
                  <div><span style={{ color: 'var(--muted)' }}>Our price</span><br /><strong>QAR {Number(row.our_price).toLocaleString()}</strong></div>
                </div>
                <div style={{ marginTop: 10, fontSize: 12, color: row.gap > 0 ? 'var(--red)' : 'var(--green)' }}>
                  Gap: {row.gap > 0 ? '+' : ''}{Number(row.gap).toLocaleString()} QAR {row.gap_pct != null ? `(${row.gap_pct}%)` : ''}
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: 'var(--dim)' }}>{row.days_listed ?? 0} days listed · {row.location || 'Qatar'}</div>
                <div style={{ marginTop: 10, fontSize: 11, color: 'var(--gold)' }}>
                  {row.gap > 15000 ? 'AI: Drop 5–8% to match' : row.gap > 0 ? 'AI: Hold or small discount' : 'AI: We are competitive'}
                </div>
              </div>
            ))}
          </div>

          {Object.keys(platformSummary).length > 0 && (
            <div className="card" style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)' }}>Platform summary</span>
              {Object.entries(platformSummary).map(([plat, data]: [string, { count: number; avg_price: number }]) => (
                <span key={plat} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 4, background: platformColor(plat) }} />
                  <span style={{ fontWeight: 600 }}>{plat}</span>
                  <span style={{ color: 'var(--dim)', fontSize: 11 }}>{data.count} listings · avg QAR {Math.round(data.avg_price).toLocaleString()}</span>
                </span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
