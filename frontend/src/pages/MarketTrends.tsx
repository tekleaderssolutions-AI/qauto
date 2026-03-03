import { useQueries } from '@tanstack/react-query'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { getMarketKpis, getMarketEvents, getMarketTrends, getMarketTrendSeries, getMarketSentiment, getMarketAnalysis } from '../api'

const gridStyle = { stroke: 'rgba(255,255,255,0.04)' }
const tooltipStyle = { background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, color: '#0f172a' }
const COLORS = ['var(--gold)', 'var(--blue)', 'var(--green)', 'var(--purple)']

export default function MarketTrends() {
  const [kpisQ, eventsQ, trendsQ, trendSeriesQ, sentimentQ, analysisQ] = useQueries({
    queries: [
      { queryKey: ['market', 'kpis'], queryFn: getMarketKpis },
      { queryKey: ['market', 'events', 10], queryFn: () => getMarketEvents(10) },
      { queryKey: ['market', 'trends'], queryFn: getMarketTrends },
      { queryKey: ['market', 'trend-series'], queryFn: () => getMarketTrendSeries(5) },
      { queryKey: ['market', 'sentiment'], queryFn: getMarketSentiment },
      { queryKey: ['market', 'analysis'], queryFn: () => getMarketAnalysis(10) },
    ],
  })
  const loading = kpisQ.isLoading && !kpisQ.data
  const backendOffline = kpisQ.isError && !kpisQ.data
  const kpis = (kpisQ.data || {}) as Record<string, number>
  const events = (eventsQ.data ?? []) as Array<{ event_name: string; start_date: string; end_date: string; demand_multiplier: number }>
  const monthlyTrends = (trendsQ.data ?? { months: [], volumes: [] }) as { months: string[]; volumes: number[] }
  const trendChartData = (trendSeriesQ.data ?? []) as Array<Record<string, unknown>>
  const sentimentData = (sentimentQ.data ?? []) as Array<{ brand: string; score: number }>
  const models = ((analysisQ.data as { models?: Array<{ make: string; model: string; trend_score: number; is_rising_3w: boolean }> })?.models ?? [])
  const trendSummaries = models.slice(0, 4).map((m, i) => ({
    label: `${m.make} ${m.model}`,
    value: `↑ ${Math.round(m.trend_score)}`,
    sub: m.is_rising_3w ? 'Rising 4 weeks' : 'Stable',
    color: COLORS[i % COLORS.length],
  }))
  const monthlyChartData = monthlyTrends.months?.length
    ? monthlyTrends.months.map((m, i) => ({ month: m || '', volume: monthlyTrends.volumes?.[i] ?? 0 }))
    : []

  if (loading) return <div className="card">Loading…</div>
  if (backendOffline) {
    return (
      <div className="card" style={{ padding: 32, textAlign: 'center', maxWidth: 520, margin: '24px auto' }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>⚠️</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--gold)', marginBottom: 8 }}>Backend is not running</div>
        <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>Start the API to see trends. Run from project root: <code style={{ background: 'var(--bg)', padding: 2, borderRadius: 4 }}>uvicorn api.main:app --reload --port 8000</code></div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Then run ETL once: <code style={{ background: 'var(--bg)', padding: 2, borderRadius: 4 }}>python etl/load_data.py</code></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--gold)', marginBottom: 3 }}>Market Trends & Economic Monitor</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Google Trends, Oil, Events & Brand Sentiment</div>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Google Trends</div>
        <div style={{ height: 220 }}>
          {trendChartData.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--muted)', fontSize: 13 }}>No Google Trends pivot data. Load <code>google_trends__model_weekly_pivot</code> via ETL.</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendChartData} margin={{ left: 20, right: 12, top: 10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStyle.stroke} />
                <XAxis
                  dataKey="week"
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                  label={{ value: 'Week', position: 'insideBottom', offset: -5, fill: '#475569', fontSize: 11 }}
                />
                <YAxis
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                  domain={[0, 100]}
                  label={{ value: 'Trend score', angle: -90, position: 'insideLeft', offset: 10, fill: '#475569', fontSize: 11 }}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="lc300" stroke="#f59e0b" strokeWidth={2} name="Land Cruiser 300" dot={{ r: 3 }} />
                <Line type="monotone" dataKey="lx600" stroke="#3b82f6" strokeWidth={2} name="Lexus LX 600" dot={{ r: 3 }} />
                <Line type="monotone" dataKey="prado" stroke="#22c55e" strokeWidth={2} name="Prado GXR" dot={{ r: 3 }} />
                <Line type="monotone" dataKey="patrol" stroke="#a78bfa" strokeWidth={2} name="Nissan Patrol" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {monthlyChartData.length > 0 && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Monthly New Car Registrations</div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthlyChartData} margin={{ left: 20, right: 12, top: 10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStyle.stroke} />
                <XAxis
                  dataKey="month"
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                  label={{ value: 'Monthly', position: 'insideBottom', offset: -5, fill: '#475569', fontSize: 11 }}
                />
                <YAxis
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                  label={{ value: 'No. of Cars', angle: -90, position: 'insideLeft', offset: 10, fill: '#475569', fontSize: 11 }}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="volume" stroke="var(--gold)" fill="rgba(245,158,11,0.2)" strokeWidth={2} name="Registrations" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
        {trendSummaries.map((t, i) => (
          <div key={i} className="card" style={{ borderLeft: `4px solid ${t.color}` }}>
            <div style={{ fontSize: 10, color: 'var(--muted)', marginBottom: 4 }}>{t.label}</div>
            <div style={{ fontSize: 20, fontWeight: 900, color: t.color }}>{t.value}</div>
            <div style={{ fontSize: 11, color: 'var(--dim)' }}>{t.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 18 }}>
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>Oil Price Tracker</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: (kpis.oil_price_usd ?? 0) > 85 ? 'var(--green)' : 'var(--gold)' }}>${kpis.oil_price_usd ?? '—'}/bbl</div>
          <div style={{ fontSize: 11, color: 'var(--dim)', marginTop: 4 }}>{kpis.oil_price_usd != null ? ((kpis.oil_price_usd > 85) ? 'Above $85 — fleet demand signal' : 'Below peak') : 'No data'}</div>
        </div>
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>Upcoming Events</div>
          <ul style={{ paddingLeft: 18, margin: 0, fontSize: 12 }}>
            {events.length === 0 ? <li style={{ color: 'var(--muted)' }}>No events in DB</li> : null}
            {events.slice(0, 5).map((e, i) => (
              <li key={i} style={{ marginBottom: 6 }}><strong>{e.event_name}</strong> — {e.start_date} (×{e.demand_multiplier})</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Social Media Sentiment By Brand</div>
        <div style={{ height: 200 }}>
          {sentimentData.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--muted)', fontSize: 13 }}>No sentiment data from API</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sentimentData} margin={{ left: 40, right: 12, top: 10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStyle.stroke} horizontal={false} />
                <XAxis
                  dataKey="brand"
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                  label={{ value: 'Brand', position: 'insideBottom', offset: -5, fill: '#475569', fontSize: 11 }}
                />
                <YAxis
                  stroke="#475569"
                  domain={[0, 100]}
                  tick={{ fontSize: 11 }}
                  label={{ value: 'Sentiment score', angle: -90, position: 'insidecenter', offset: 1, fill: '#475569', fontSize: 11 }}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="score" radius={[4, 4, 0, 0]} fill="var(--gold)" name="Sentiment score" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  )
}
