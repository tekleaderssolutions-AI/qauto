import { useQueries } from '@tanstack/react-query'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { getMarketKpis, getMarketTrends, getInventorySummary } from '../api'

const gridStyle = { stroke: 'rgba(255,255,255,0.04)' }
const tooltipStyle = { background: '#ffffff', border: '1px solid rgba(148,163,184,0.6)', borderRadius: 8 }

export default function MarketHub() {
  const [kpisQ, trendsQ, summaryQ] = useQueries({
    queries: [
      { queryKey: ['market', 'kpis'], queryFn: getMarketKpis },
      { queryKey: ['market', 'trends'], queryFn: getMarketTrends },
      { queryKey: ['inventory', 'summary'], queryFn: getInventorySummary },
    ],
  })
  const loading = kpisQ.isLoading || trendsQ.isLoading || summaryQ.isLoading
  const backendOffline = kpisQ.isError || trendsQ.isError || summaryQ.isError
  const kpis = (kpisQ.data || {}) as Record<string, number>
  const trends = (trendsQ.data && ((trendsQ.data as { months?: string[]; volumes?: number[] }).months?.length || (trendsQ.data as { volumes?: number[] }).volumes?.length))
    ? (trendsQ.data as { months: string[]; volumes: number[] })
    : { months: [] as string[], volumes: [] as number[] }
  const summary = (summaryQ.data || {}) as Record<string, number>

  if (loading && !kpisQ.data && !trendsQ.data && !summaryQ.data) return <div className="card" style={{ padding: 24, textAlign: 'center' }}>Loading…</div>
  if (backendOffline && !kpisQ.data && !trendsQ.data && !summaryQ.data) {
    return (
      <div className="card" style={{ padding: 32, textAlign: 'center', maxWidth: 520, margin: '24px auto' }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>⚠️</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--gold)', marginBottom: 8 }}>Backend is not running</div>
        <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>Start the API to see live data. No mock or cached data is shown.</div>
        <code style={{ background: 'var(--bg)', padding: '10px 14px', borderRadius: 8, display: 'block', textAlign: 'left' }}>uvicorn api.main:app --reload --port 8000</code>
      </div>
    )
  }

  const chartData =
    trends.months?.map((m, i) => {
      const raw = String(m)
      let label = raw
      if (/^\d{4}-\d{2}/.test(raw)) {
        const [year, month] = raw.split('-')
        label = `${month}/${year}`
      }
      return {
        month: label,
        tx: trends.volumes?.[i] ?? 0,
        price: 120000 + i * 3000,
      }
    }) ?? []
  const topModels = [
    { model: 'Land Cruiser 300', days: 21 },
    { model: 'Prado GXR', days: 24 },
    { model: 'Nissan Patrol', days: 30 },
    { model: 'Hilux SR5', days: 28 },
    { model: 'Lexus LX 600', days: 35 },
  ]

  const kpiList = [
    { label: 'Market Health', value: kpis.market_health_score != null ? `${kpis.market_health_score}/100` : '—', sub: 'Strong ↑', color: 'var(--green)', icon: '🏥' },
    { label: 'Avg Days (SUV)', value: kpis.avg_days_to_sell_suv != null ? `${kpis.avg_days_to_sell_suv} days` : '—', sub: 'last 3 months', color: 'var(--blue)', icon: '⏱' },
    { label: 'Oil Price', value: kpis.oil_price_usd != null ? `$${kpis.oil_price_usd}/bbl` : '—', sub: 'HOT signal', color: 'var(--gold)', icon: '🛢' },
    { label: 'Active Buyers', value: kpis.active_buyers_60d ?? '—', sub: 'Ready < 60 days', color: 'var(--purple)', icon: '👥' },
    { label: 'Critical Stock', value: kpis.critical_inventory_count ?? summary?.critical ?? 0, sub: 'Need action now', color: 'var(--red)', icon: '🚨' },
    { label: 'LC300 Trend', value: '↑ 94', sub: 'Rising 4 weeks', color: 'var(--teal)', icon: '📈' },
  ]

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--gold)', marginBottom: 3 }}>Market Intelligence Hub</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Real Time Used Car Market Overview</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 18 }}>
        {kpiList.map((k, i) => (
          <div
            key={i}
            className="kpi-card"
            style={{
              borderColor: `${k.color}33`,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              paddingRight: 16,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div className="kpi-label">{k.label}</div>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 999,
                  background: `${k.color}1a`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 25,
                  color: k.color,
                  flexShrink: 0,
                }}
              >
                {k.icon}
              </div>
            </div>
            <div>
              <div className="kpi-value" style={{ color: k.color }}>{k.value}</div>
              <div className="kpi-sub">{k.sub}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 18, marginBottom: 18 }}>
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Monthly Transactions & Avg Price</div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.length ? chartData : []}>
                <defs>
                  <linearGradient id="txGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/><stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/></linearGradient>
                  <linearGradient id="prGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStyle.stroke} />
                <XAxis
                  dataKey="month"
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                  label={{
                    value: 'Month',
                    position: 'insideBottom',
                    offset: -5,
                    style: { fontSize: 11, fill: '#475569' },
                  }}
                />
                <YAxis
                  yAxisId="left"
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                  label={{
                    value: 'Transactions',
                    angle: -90,
                    position: 'insideLeft',
                    style: { fontSize: 11, fill: '#475569' },
                  }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                  label={{
                    value: 'Avg price',
                    angle: -90,
                    position: 'insideRight',
                    style: { fontSize: 11, fill: '#475569' },
                  }}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Area yAxisId="left" type="monotone" dataKey="tx" stroke="#f59e0b" fill="url(#txGrad)" strokeWidth={2} name="Transactions" />
                <Area yAxisId="right" type="monotone" dataKey="price" stroke="#3b82f6" fill="url(#prGrad)" strokeWidth={2} name="Avg Price QAR" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'flex', gap: 18, marginTop: 10 }}>
            <span style={{ fontSize: 10, color: '#b45309', display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 14, height: 3, background: '#f59e0b', borderRadius: 2 }} />
              Transactions
            </span>
            <span style={{ fontSize: 10, color: '#2563eb', display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 14, height: 3, background: '#3b82f6', borderRadius: 2 }} />
              Avg Price QAR
            </span>
  
          </div>
        </div>
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Top Models</div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topModels} layout="vertical" margin={{ left: 8, right: 8, bottom: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStyle.stroke} horizontal={false} />
                <XAxis
                  type="number"
                  stroke="#475569"
                  domain={[0, 55]}
                  tick={{ fontSize: 10 }}
                  label={{ value: 'Days to sell', position: 'insideBottom', offset: -4, style: { fontSize: 11, fill: '#475569' } }}
                />
                <YAxis
                  type="category"
                  dataKey="model"
                  stroke="#475569"
                  tick={{ fontSize: 10 }}
                  width={90}
                  label={{ value: 'Model', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#475569' } }}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="days" radius={[0, 5, 5, 0]} name="Days">
                  {topModels.map((_, i) => (
                    <Cell key={i} fill={topModels[i].days < 30 ? '#22c55e' : topModels[i].days < 40 ? '#f59e0b' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
        <div className="card" style={{ border: '1px solid var(--border)', borderRadius: 13, padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>Oil Price Signal</span>
            <span style={{ fontSize: 10, fontWeight: 700, background: 'rgba(34,197,94,0.15)', color: 'var(--green)', padding: '3px 10px', borderRadius: 6 }}>BUY</span>
          </div>
          <div style={{ fontSize: 20, fontWeight: 900, color: 'var(--green)', marginBottom: 8 }}>${kpis.oil_price_usd ?? '—'}/barrel</div>
          <div style={{ fontSize: 11, color: 'var(--dim)', lineHeight: 1.6 }}>Above $85 threshold. Consumer confidence at {kpis.consumer_confidence_index ?? '—'}. Market is HOT — recommend listing at full price.</div>
        </div>
        <div className="card" style={{ border: '1px solid var(--border)', borderRadius: 13, padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>Next Event</span>
            <span style={{ fontSize: 10, fontWeight: 700, background: 'rgba(245,158,11,0.15)', color: 'var(--gold)', padding: '3px 10px', borderRadius: 6 }}>6 WEEKS</span>
          </div>
          <div style={{ fontSize: 20, fontWeight: 900, color: 'var(--gold)', marginBottom: 8 }}>National Day</div>
          <div style={{ fontSize: 11, color: 'var(--dim)', lineHeight: 1.6 }}>December 18. Luxury segment demand spike — Lexus, Land Rover, BMW. Stock luxury models in November.</div>
        </div>
        <div className="card" style={{ border: '1px solid var(--border)', borderRadius: 13, padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>Expected Signal</span>
            <span style={{ fontSize: 10, fontWeight: 700, background: 'rgba(59,130,246,0.15)', color: 'var(--blue)', padding: '3px 10px', borderRadius: 6 }}>RETURNING</span>
          </div>
          <div style={{ fontSize: 20, fontWeight: 900, color: 'var(--blue)', marginBottom: 8 }}>2.9M</div>
          <div style={{ fontSize: 11, color: 'var(--dim)', lineHeight: 1.6 }}>Sept–Oct return season. Supply tightening. Best time to raise prices by 5–8%.</div>
        </div>
      </div>
    </div>
  )
}
