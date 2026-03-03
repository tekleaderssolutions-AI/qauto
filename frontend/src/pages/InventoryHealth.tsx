import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getInventory, getInventorySummary } from '../api'

const COLOR_HEX: Record<string, string> = {
  white: '#f8fafc', pearl: '#f1f5f9', silver: '#cbd5e1', black: '#1e293b', grey: '#64748b', graphite: '#475569',
  red: '#dc2626', blue: '#2563eb', green: '#16a34a', beige: '#d4b896', brown: '#92400e', ivory: '#ffefd5', cream: '#fffdd0', bronze: '#cd7f32',
}

function colorSwatch(name: string) {
  if (!name) return '#334155'
  const n = String(name).toLowerCase()
  for (const [k, v] of Object.entries(COLOR_HEX)) {
    if (n.includes(k)) return v
  }
  return '#64748b'
}

type Item = {
  vehicle_id: number
  make: string
  model: string
  trim: string
  year: number
  color_exterior: string
  days_in_stock: number
  list_price_qar: number
  risk_score: number
  risk_flag: string
  recommended_action?: string
  body_type: string
}

function actionLabel(row: Item): string {
  const {
    risk_flag,
    days_in_stock: days,
    list_price_qar,
    risk_score,
    recommended_action,
    year,
    body_type,
    make,
    model,
    trim,
  } = row

  if (recommended_action && recommended_action.trim() !== '') {
    return recommended_action
  }

  const risk = risk_flag === 'at_risk' ? 'risk' : risk_flag
  const price = Number(list_price_qar) || 0

  let minPct = 0
  let maxPct = 0

  if (risk === 'healthy') {
    minPct = 0
    maxPct = 0
  } else if (risk === 'monitor') {
    minPct = days > 120 ? 2 : 0
    maxPct = days > 150 ? 5 : 3
  } else if (risk === 'risk' || risk === 'critical') {
    const ageFactor = Math.max(0, Math.min(8, Math.round((new Date().getFullYear() - year) / 2)))
    const daysFactor = Math.max(2, Math.min(10, Math.round(days / 60)))
    const scoreFactor = Math.max(0, Math.min(6, Math.round((risk_score - 50) / 8)))
    const base = daysFactor + ageFactor + scoreFactor
    minPct = Math.max(4, Math.min(14, base - 2))
    maxPct = Math.max(minPct + 1, Math.min(18, base + 2))
  }

  const minAmt = Math.round((price * minPct) / 100)
  const maxAmt = Math.round((price * maxPct) / 100)

  const base = (() => {
    if (risk === 'healthy') return 'Keep price and merchandising as-is'
    if (risk === 'monitor') {
      if (minPct === 0 && maxPct === 0) {
        return 'Refresh listing and only adjust price if inquiries drop'
      }
      return `Light price test of ${minPct}–${maxPct}% (≈ QAR ${minAmt.toLocaleString()}–${maxAmt.toLocaleString()})`
    }
    if (risk === 'risk') {
      return `Mark down ${minPct}–${maxPct}% (≈ QAR ${minAmt.toLocaleString()}–${maxAmt.toLocaleString()}) and re‑promote`
    }
    if (risk === 'critical') {
      if (days > 210) {
        return `Move to auction / wholesale or take a ${minPct}–${maxPct}% discount (≈ QAR ${minAmt.toLocaleString()}–${maxAmt.toLocaleString()})`
      }
      return `Aggressive markdown of ${minPct}–${maxPct}% (≈ QAR ${minAmt.toLocaleString()}–${maxAmt.toLocaleString()})`
    }
    return 'Review price and merchandising versus live market'
  })()

  const vehicleLabel = `${year} ${make} ${model} ${trim}`.trim()

  const detail = (() => {
    if (risk === 'healthy') {
      return `Good turn: ${vehicleLabel} at ${days} days in stock for a ${body_type.toLowerCase()} — keep in main lane and only adjust if market shifts.`
    }
    if (risk === 'monitor') {
      if (days < 120) {
        return `${vehicleLabel} is starting to age at ${days} days — refresh hero photos, tighten description, and make sure it appears in brand search results.`
      }
      return `${vehicleLabel} has been in stock ${days} days — check price vs direct comps and improve merchandising before taking a bigger discount.`
    }
    if (risk === 'risk') {
      return `${vehicleLabel} is a slow mover at ${days} days with risk score ${risk_score} — capital is tied up, feature it in weekly offers, cross‑list on external classifieds, and have sales follow up on all leads.`
    }
    if (risk === 'critical') {
      if (days > 240) {
        return `${vehicleLabel} is extremely aged at ${days} days — treat as exit stock, move to manager specials, and target a 30‑day sell‑out window.`
      }
      return `${vehicleLabel} is very slow at ${days} days — reduce reconditioning spend, push to auction/wholesale channels if response remains weak after price change.`
    }
    return `${vehicleLabel} has ${days} days in stock — validate demand, pricing, and channel mix versus live market.`
  })()

  return `${base} — ${detail}`
}

export default function InventoryHealth() {
  const [filter, setFilter] = useState<string | null>(null)
  const summaryQ = useQuery({
    queryKey: ['inventory', 'summary'],
    queryFn: getInventorySummary,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })
  const listQ = useQuery({
    queryKey: ['inventory', 'list', filter ?? 'all'],
    queryFn: () => getInventory({ risk_flag: filter ?? undefined, limit: 15 }),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })
  const summary = (summaryQ.data || {}) as Record<string, number>
  const items = (listQ.data as { items?: Item[]; total?: number } | undefined)?.items ?? []
  const total = (listQ.data as { total?: number } | undefined)?.total ?? 0
  const loading = listQ.isLoading

  const atRiskCount = (summary.at_risk ?? summary.risk ?? 0)
  const totalCount =
    (summary.healthy ?? 0) +
    (summary.monitor ?? 0) +
    atRiskCount +
    (summary.critical ?? 0) || 1
  const riskBars = [
    { key: 'healthy', label: 'Healthy', color: 'var(--green)', count: summary.healthy ?? 0 },
    { key: 'monitor', label: 'Monitor', color: 'var(--gold)', count: summary.monitor ?? 0 },
    { key: 'at_risk', label: 'At Risk', color: 'var(--orange)', count: atRiskCount },
    { key: 'critical', label: 'Critical', color: 'var(--red)', count: summary.critical ?? 0 },
  ]

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--gold)', marginBottom: 3 }}>Inventory Health Monitor</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Risk Scored Stock With Recommended Actions</div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        {['All', 'Healthy', 'Monitor', 'At Risk', 'Critical'].map((label) => {
          const key = label === 'All' ? null : label.toLowerCase().replace(' ', '_')
          const count = label === 'All' ? totalCount : (summary[key as keyof typeof summary] ?? 0)
          return (
            <button
              key={label}
              className={`pill ${filter === key ? 'active' : ''}`}
              onClick={() => setFilter(key)}
            >
              {label} ({count})
            </button>
          )
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
        {riskBars.map(({ key, label, color, count }) => (
          <div key={key} className="card" style={{ padding: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)' }}>{label}</span>
              <span style={{ fontSize: 18, fontWeight: 900, color }}>{count}</span>
            </div>
            <div style={{ height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${(count / totalCount) * 100}%`, height: '100%', background: color, borderRadius: 3 }} />
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ overflow: 'auto', padding: 0 }}>
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted)' }}>Loading inventory…</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Risk</th>
                <th>Vehicle</th>
                <th>Manufacturer Year</th>
                <th>Color</th>
                <th>Days in Stock</th>
                <th>Listed Price</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.vehicle_id}>
                  <td>
                    <span className={`badge badge-${row.risk_flag}`}>
                      {row.risk_flag === 'at_risk' ? 'risk' : row.risk_flag}
                    </span>
                  </td>
                  <td>{row.make} {row.model} {row.trim}</td>
                  <td>{row.year}</td>
                  <td>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 16, height: 16, borderRadius: 4, background: colorSwatch(row.color_exterior), border: '1px solid rgba(255,255,255,0.2)' }} />
                      {row.color_exterior || '—'}
                    </span>
                  </td>
                  <td>{row.days_in_stock}</td>
                  <td>QAR {Number(row.list_price_qar).toLocaleString()}</td>
                  <td style={{ fontWeight: 600, color: 'var(--gold)', maxWidth: 420 }}>
                    {actionLabel(row)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ padding: '10px 13px', color: 'var(--muted)', fontSize: 11 }}>Total: {total}</div>
      </div>
    </div>
  )
}
