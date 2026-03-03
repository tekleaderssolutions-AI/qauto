const BASE = '/api'

export async function getMarketKpis() {
  const r = await fetch(`${BASE}/market/kpis`)
  if (!r.ok) throw new Error('Failed to fetch KPIs')
  return r.json()
}

export async function getMarketTrends() {
  const r = await fetch(`${BASE}/market/trends`)
  if (!r.ok) return { months: [], volumes: [] }
  return r.json()
}

export async function getMarketAnalysis(limit = 20) {
  const r = await fetch(`${BASE}/market/analysis?limit=${limit}`)
  if (!r.ok) return { models: [], briefing: '' }
  return r.json()
}

export async function getMarketTrendSeries(weeks = 5) {
  const r = await fetch(`${BASE}/market/trend-series?weeks=${weeks}`)
  if (!r.ok) return []
  return r.json()
}

export async function getMarketSentiment() {
  const r = await fetch(`${BASE}/market/sentiment`)
  if (!r.ok) return []
  return r.json()
}

export async function getMarketEvents(limit: number = 10) {
  const r = await fetch(`${BASE}/market/events?limit=${limit}`)
  if (!r.ok) return []
  return r.json()
}

export async function getMarketOilSeries(limit = 24) {
  const r = await fetch(`${BASE}/market/oil-series?limit=${limit}`)
  if (!r.ok) return { months: [], oil_price: [] }
  return r.json() as Promise<{ months: string[]; oil_price: number[] }>
}

export async function getInventorySummary() {
  const r = await fetch(`${BASE}/inventory/summary`)
  if (!r.ok) throw new Error('Failed to fetch inventory summary')
  return r.json()
}

export async function getInventory(params: Record<string, string | number | undefined> = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => v != null && q.set(k, String(v)))
  const r = await fetch(`${BASE}/inventory?${q}`)
  if (!r.ok) throw new Error('Failed to fetch inventory')
  return r.json()
}

export async function getPrice(body: {
  make: string
  model: string
  trim?: string
  year: number
  mileage_km?: number
  color_exterior?: string
  body_type?: string
  sunroof_flag?: boolean
  ventilated_seats_flag?: boolean
}) {
  const r = await fetch(`${BASE}/price`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error('Failed to get price')
  return r.json()
}

export async function getReadyBuyers(limit = 20) {
  const r = await fetch(`${BASE}/match/ready-buyers?limit=${limit}`)
  if (!r.ok) throw new Error('Failed to fetch buyers')
  return r.json()
}

export async function getMatches(customerId: number, topN = 5) {
  const r = await fetch(`${BASE}/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_id: customerId, top_n: topN }),
  })
  if (!r.ok) throw new Error('Failed to get matches')
  return r.json()
}

export async function getMatchDashboard(topPerBuyer = 3) {
  const r = await fetch(`${BASE}/match/dashboard?top_per_buyer=${topPerBuyer}`)
  if (!r.ok) throw new Error('Failed to fetch match dashboard')
  return r.json()
}

export async function chat(message: string) {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!r.ok) throw new Error('Failed to chat')
  return r.json()
}

export async function getCompetitors(params: { model_filter?: string; search?: string; sort?: string; limit?: number } = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => v != null && q.set(k, String(v)))
  const r = await fetch(`${BASE}/competitors?${q}`)
  if (!r.ok) throw new Error('Failed to fetch competitors')
  return r.json()
}

export async function getPricingOptions() {
  const r = await fetch(`${BASE}/pricing/options`)
  if (!r.ok) throw new Error('Failed to fetch pricing options')
  return r.json() as Promise<{ makes: string[]; models: string[]; trims: string[] }>
}
