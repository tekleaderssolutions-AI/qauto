/** Skeleton loader shown while lazy-loaded dashboard chunks load. */
export default function DashboardSkeleton() {
  return (
    <div className="card" style={{ padding: 24 }}>
      <div style={{ display: 'flex', gap: 12, marginBottom: 18, flexWrap: 'wrap' }}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} style={{ width: 140, height: 70, background: 'rgba(255,255,255,0.06)', borderRadius: 10 }} />
        ))}
      </div>
      <div style={{ height: 200, background: 'rgba(255,255,255,0.06)', borderRadius: 10, marginBottom: 18 }} />
      <div style={{ height: 120, background: 'rgba(255,255,255,0.06)', borderRadius: 10 }} />
    </div>
  )
}
