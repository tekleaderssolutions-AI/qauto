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

function actionLabel(risk: string, days: number, existing?: string): string {
  if (existing && existing !== '') return existing
  if (risk === 'healthy') return 'Hold'
  if (risk === 'monitor') return 'Review'
  if (risk === 'at_risk') return days > 120 ? 'Drop 7%' : 'Review'
  if (risk === 'critical') return days > 180 ? 'Auction' : days > 150 ? 'Drop 16%' : 'Drop 10%'
  return 'Review'
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

export default function InventoryHealth() {
  const [filter, setFilter] = useState<string | null>(null)
  const summaryQ = useQuery({ queryKey: ['inventory', 'summary'], queryFn: getInventorySummary })
  const listQ = useQuery({
    queryKey: ['inventory', 'list', filter ?? 'all'],
    queryFn: () => getInventory({ risk_flag: filter ?? undefined, limit: 100 }),
  })
  const summary = (summaryQ.data || {}) as Record<string, number>
  const items = (listQ.data as { items?: Item[]; total?: number } | undefined)?.items ?? []
  const total = (listQ.data as { total?: number } | undefined)?.total ?? 0
  const loading = listQ.isLoading

  const totalCount = (summary.healthy ?? 0) + (summary.monitor ?? 0) + (summary.at_risk ?? 0) + (summary.critical ?? 0) || 1
  const riskBars = [
    { key: 'healthy', label: 'Healthy', color: 'var(--green)', count: summary.healthy ?? 0 },
    { key: 'monitor', label: 'Monitor', color: 'var(--gold)', count: summary.monitor ?? 0 },
    { key: 'at_risk', label: 'At Risk', color: 'var(--orange)', count: summary.at_risk ?? 0 },
    { key: 'critical', label: 'Critical', color: 'var(--red)', count: summary.critical ?? 0 },
  ]

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--gold)', marginBottom: 3 }}>Inventory Health Monitor</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Risk-scored stock with recommended actions</div>
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
                <th>Year</th>
                <th>Color</th>
                <th>Days in Stock</th>
                <th>Listed Price</th>
                <th>AI Price</th>
                <th>Gap</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.vehicle_id}>
                  <td><span className={`badge badge-${row.risk_flag}`}>{row.risk_flag}</span></td>
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
                  <td style={{ color: 'var(--dim)' }}>—</td>
                  <td style={{ color: 'var(--dim)' }}>—</td>
                  <td style={{ fontWeight: 600, color: 'var(--gold)' }}>{actionLabel(row.risk_flag, row.days_in_stock, row.recommended_action)}</td>
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
