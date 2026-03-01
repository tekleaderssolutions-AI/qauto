import { useState, useCallback } from 'react'
import { getPrice } from '../api'

const COLORS = [
  { name: 'White', hex: '#f8fafc' }, { name: 'Pearl White', hex: '#f1f5f9' }, { name: 'Silver', hex: '#cbd5e1' },
  { name: 'Black', hex: '#1e293b' }, { name: 'Grey', hex: '#64748b' }, { name: 'Red', hex: '#dc2626' },
  { name: 'Blue', hex: '#2563eb' }, { name: 'Beige', hex: '#d4b896' }, { name: 'Brown', hex: '#92400e' },
]

function parseCSV(text: string): Record<string, string>[] {
  const lines = text.trim().split(/\r?\n/)
  if (lines.length < 2) return []
  const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''))
  const rows: Record<string, string>[] = []
  for (let i = 1; i < lines.length; i++) {
    const vals = lines[i].split(',').map((v) => v.trim().replace(/^"|"$/g, ''))
    const row: Record<string, string> = {}
    headers.forEach((h, j) => { row[h] = vals[j] ?? '' })
    rows.push(row)
  }
  return rows
}

function analyzeCarRow(row: Record<string, string>): { score: number; verdict: string; insights: string[] } {
  const color = (row.color_exterior || row.Color || row.color || '').toLowerCase()
  const model = (row.model || row.Model || '').toLowerCase()
  const make = (row.make || row.Make || '').toLowerCase()
  const year = parseInt(row.year || row.Year || '0', 10) || new Date().getFullYear()
  const mileage = parseInt(row.mileage_km || row.mileage || row.Mileage_km || '0', 10) || 0
  const accident = (row.accident_history || row.accident || '').toLowerCase()
  const service = (row.service_history || row.service || '').toLowerCase()
  let score = 50
  const insights: string[] = []
  if (['white', 'pearl', 'silver', 'black'].some((c) => color.includes(c))) {
    score += 12
    insights.push('Preferred color')
  } else if (['red', 'blue', 'green'].some((c) => color.includes(c))) {
    score -= 10
    insights.push('Slower-moving color')
  }
  if (['land cruiser', 'prado', 'patrol', 'hilux', 'fortuner', 'lexus'].some((m) => model.includes(m) || make.includes('toyota') || make.includes('nissan'))) {
    score += 10
    insights.push('High demand model')
  }
  const age = new Date().getFullYear() - year
  if (age <= 2) { score += 8; insights.push('Near-new') } else if (age >= 8) { score -= 15; insights.push('Older unit') }
  if (mileage > 0 && mileage < 60000) { score += 5 } else if (mileage > 200000) { score -= 10; insights.push('High mileage') }
  if (accident.includes('no') || accident === '0' || !accident) { score += 5 } else { score -= 20; insights.push('Accident history') }
  if (service.includes('full') || service.includes('dealer')) { score += 5; insights.push('Full service') }
  score = Math.max(0, Math.min(100, score))

  let verdict = 'CONSIDER'
  if (score >= 75) verdict = 'STRONG BUY'
  else if (score >= 60) verdict = 'BUY'
  else if (score >= 40) verdict = 'CONSIDER'
  else if (score >= 25) verdict = 'AVOID'
  else verdict = 'DO NOT BUY'
  return { score, verdict, insights }
}

const SAMPLE_CSV = `make,model,trim,year,color_exterior,mileage_km,asking_price_qar,accident_history,service_history
Toyota,Land Cruiser,GXR,2022,White,45000,285000,No,Full dealer
Nissan,Patrol,TI,2021,Grey,78000,320000,No,Full
Toyota,Prado,VX,2020,Red,120000,195000,Yes,Independent`

export default function PricingTool() {
  const [make, setMake] = useState('Toyota')
  const [model, setModel] = useState('Land Cruiser')
  const [trim, setTrim] = useState('GXR')
  const [year, setYear] = useState(2023)
  const [color, setColor] = useState('White')
  const [mileage, setMileage] = useState(50000)
  const [bodyType, setBodyType] = useState('SUV')
  const [sunroof, setSunroof] = useState(false)
  const [ventilated, setVentilated] = useState(true)
  const [result, setResult] = useState<{
    recommended_price_qar: number
    price_range_low: number
    price_range_high: number
    confidence_pct: number
    time_to_sell_days?: number
    time_to_sell_fast_days?: number
    time_to_sell_max_days?: number
    similar_transactions_count?: number
    market_context?: string[]
    ai_advice?: string
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [csvResults, setCsvResults] = useState<Array<Record<string, string> & { _score?: number; _verdict?: string; _insights?: string[] }>>([])
  const [csvFilter, setCsvFilter] = useState<string>('All')
  const [dragging, setDragging] = useState(false)

  const submit = () => {
    setError('')
    setLoading(true)
    getPrice({
      make,
      model,
      trim,
      year,
      mileage_km: mileage,
      color_exterior: color,
      body_type: bodyType,
      sunroof_flag: sunroof,
      ventilated_seats_flag: ventilated,
    })
      .then(setResult)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  const onFile = useCallback((file: File) => {
    const r = new FileReader()
    r.onload = () => {
      const text = String(r.result)
      const rows = parseCSV(text)
      const analyzed = rows.map((row) => {
        const { score, verdict, insights } = analyzeCarRow(row)
        return { ...row, _score: score, _verdict: verdict, _insights: insights }
      })
      setCsvResults(analyzed)
    }
    r.readAsText(file)
  }, [])

  const filteredCsv = csvFilter === 'All'
    ? csvResults
    : csvResults.filter((r) => r._verdict === csvFilter.replace(' ', ' '))
  const strongBuy = csvResults.filter((r) => r._verdict === 'STRONG BUY')
  const buy = csvResults.filter((r) => r._verdict === 'BUY')
  const totalProfitBanner = (strongBuy.length + buy.length) > 0

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--gold)', marginBottom: 3 }}>Pricing Intelligence Tool</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Single car or bulk CSV · AI price + buy/sell verdict</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 20, marginBottom: 24 }}>
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Car details</div>
          <div style={{ display: 'grid', gap: 12 }}>
            <label><span style={{ fontSize: 10, color: 'var(--muted)' }}>Make</span><br /><input value={make} onChange={(e) => setMake(e.target.value)} style={{ width: '100%' }} /></label>
            <label><span style={{ fontSize: 10, color: 'var(--muted)' }}>Model / Trim</span><br /><div style={{ display: 'flex', gap: 8 }}><input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model" style={{ flex: 1 }} /><input value={trim} onChange={(e) => setTrim(e.target.value)} placeholder="Trim" style={{ width: 80 }} /></div></label>
            <label><span style={{ fontSize: 10, color: 'var(--muted)' }}>Year</span><br /><input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} style={{ width: '100%' }} /></label>
            <div>
              <span style={{ fontSize: 10, color: 'var(--muted)' }}>Color</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
                {COLORS.map((c) => (
                  <button
                    key={c.name}
                    type="button"
                    onClick={() => setColor(c.name)}
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 8,
                      border: color === c.name ? '2px solid var(--gold)' : '1px solid rgba(255,255,255,0.2)',
                      background: c.hex,
                      cursor: 'pointer',
                      padding: 0,
                    }}
                    title={c.name}
                  />
                ))}
              </div>
            </div>
            <div>
              <span style={{ fontSize: 10, color: 'var(--muted)' }}>Mileage (km) — {mileage.toLocaleString()}</span>
              <input type="range" min={0} max={300000} step={5000} value={mileage} onChange={(e) => setMileage(Number(e.target.value))} style={{ width: '100%', marginTop: 4 }} />
            </div>
            <label><span style={{ fontSize: 10, color: 'var(--muted)' }}>Body type</span><br /><input value={bodyType} onChange={(e) => setBodyType(e.target.value)} style={{ width: '100%' }} /></label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}><input type="checkbox" checked={sunroof} onChange={(e) => setSunroof(e.target.checked)} /> Sunroof</label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}><input type="checkbox" checked={ventilated} onChange={(e) => setVentilated(e.target.checked)} /> Ventilated seats</label>
          </div>
          <button className="btn-gold" onClick={submit} disabled={loading} style={{ marginTop: 16 }}>
            {loading ? 'Calculating…' : 'Get AI Price'}
          </button>
        </div>

        <div className="card">
          {error && <div style={{ color: 'var(--red)', marginBottom: 12, fontSize: 12 }}>{error}</div>}
          {result && (
            <>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>AI Recommendation</div>
              <div style={{ fontSize: 28, fontWeight: 900, color: 'var(--gold)', marginBottom: 8 }}>QAR {result.recommended_price_qar.toLocaleString()}</div>
              <div style={{ fontSize: 12, color: 'var(--dim)', marginBottom: 14 }}>
                Range: QAR {result.price_range_low.toLocaleString()} – QAR {result.price_range_high.toLocaleString()}
                {result.similar_transactions_count != null && result.similar_transactions_count > 0 && (
                  <span style={{ color: 'var(--green)', marginLeft: 8 }}>· {result.confidence_pct.toFixed(0)}% Confidence ({result.similar_transactions_count} similar transactions)</span>
                )}
                {(result.similar_transactions_count == null || result.similar_transactions_count === 0) && (
                  <span> · {result.confidence_pct.toFixed(0)}% Confidence</span>
                )}
              </div>
              <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 10, padding: 12, marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8 }}>Time to sell</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                  <div>QAR {(result.recommended_price_qar).toLocaleString()}: ~{result.time_to_sell_days ?? 28} days</div>
                  <div>Fast sale (-6%): ~{result.time_to_sell_fast_days ?? 14} days</div>
                  <div>Max price (+6%): ~{result.time_to_sell_max_days ?? 48} days</div>
                </div>
              </div>
              {(result.market_context?.length ?? 0) > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>Market context</div>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--dim)', lineHeight: 1.6 }}>
                    {result.market_context!.map((item, i) => (
                      <li key={i} style={{ color: 'var(--green)' }}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.ai_advice && (
                <div style={{ marginTop: 10, padding: 12, background: 'rgba(245,158,11,0.08)', borderRadius: 10, borderLeft: '4px solid var(--gold)' }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>AI advice</div>
                  <div style={{ fontSize: 13, color: 'var(--gold)', lineHeight: 1.5 }}>{result.ai_advice}</div>
                </div>
              )}
              {!result.ai_advice && (result.market_context?.length ?? 0) === 0 && (
                <div style={{ fontSize: 11, color: 'var(--dim)' }}>Market context: SUV segment strong. White/silver move 15% faster in Qatar. Add GROQ_API_KEY for detailed AI advice.</div>
              )}
            </>
          )}
          {!result && !error && <div style={{ color: 'var(--muted)', fontSize: 12 }}>Enter details and click Get AI Price.</div>}
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 20, marginTop: 20 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>Or analyse a bulk list (CSV)</div>
        <div
          className={`drop-zone ${dragging ? 'dragover' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f?.name.endsWith('.csv')) onFile(f) }}
          onClick={() => document.getElementById('csv-input')?.click()}
        >
          <input id="csv-input" type="file" accept=".csv" style={{ display: 'none' }} onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
          Drop CSV here or click to upload · Columns: make, model, trim, year, color_exterior, mileage_km, asking_price_qar, accident_history, service_history
        </div>
        <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(SAMPLE_CSV)}`} download="sample_bulk.csv" style={{ display: 'inline-block', marginTop: 10, fontSize: 12, color: 'var(--gold)' }}>Download Sample CSV</a>

        {csvResults.length > 0 && (
          <>
            {totalProfitBanner && (
              <div style={{ background: 'linear-gradient(135deg, rgba(34,197,94,0.2), rgba(34,197,94,0.08))', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 12, padding: 14, marginTop: 16, marginBottom: 14 }}>
                <strong style={{ color: 'var(--green)' }}>Total profit potential</strong> — {strongBuy.length} Strong Buy + {buy.length} Buy in this list. Prioritise these units.
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, marginTop: 12, marginBottom: 12, flexWrap: 'wrap' }}>
              {['All', 'STRONG BUY', 'BUY', 'CONSIDER', 'AVOID'].map((f) => (
                <button key={f} className={`pill ${csvFilter === f ? 'active' : ''}`} onClick={() => setCsvFilter(f)}>{f}</button>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {filteredCsv.map((row, i) => (
                <div key={i} className="card" style={{ borderLeft: `4px solid ${row._verdict === 'STRONG BUY' ? 'var(--green)' : row._verdict === 'BUY' ? 'var(--blue)' : row._verdict === 'AVOID' || row._verdict === 'DO NOT BUY' ? 'var(--red)' : 'var(--gold)'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 18, fontWeight: 900 }}>{row._score ?? 0}</span>
                    <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 6, background: row._verdict === 'STRONG BUY' ? 'rgba(34,197,94,0.2)' : row._verdict === 'BUY' ? 'rgba(59,130,246,0.2)' : row._verdict === 'AVOID' || row._verdict === 'DO NOT BUY' ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)', color: 'var(--text)' }}>{row._verdict}</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>{row.make} {row.model} {row.trim} {row.year}</div>
                  <div style={{ fontSize: 11, color: 'var(--dim)', marginBottom: 8 }}>Asking QAR {(row.asking_price_qar || row.asking_price || row.price || 0).toLocaleString()} · {(row.mileage_km || row.mileage || 0).toLocaleString()} km</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {(row._insights || []).map((ins, j) => (
                      <span key={j} style={{ fontSize: 10, background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: 4 }}>{ins}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
