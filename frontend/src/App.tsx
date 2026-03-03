import { lazy, Suspense } from 'react'
import { Routes, Route, NavLink, Navigate, useLocation, useNavigate } from 'react-router-dom'
import DashboardSkeleton from './components/ui/DashboardSkeleton'

const MarketHub = lazy(() => import('./pages/MarketHub'))
const InventoryHealth = lazy(() => import('./pages/InventoryHealth'))
const PricingTool = lazy(() => import('./pages/PricingTool'))
const MarketTrends = lazy(() => import('./pages/MarketTrends'))
const BuyerMatcher = lazy(() => import('./pages/BuyerMatcher'))
const AIAdvisor = lazy(() => import('./pages/AIAdvisor'))
const CompetitorPrices = lazy(() => import('./pages/CompetitorPrices'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))

const nav = [
  { to: '/', label: 'Market Hub' },
  { to: '/inventory', label: 'Inventory' },
  { to: '/pricing', label: 'Pricing Tool' },
  { to: '/competitors', label: 'Competitors' },
  { to: '/trends', label: 'Trends' },
  { to: '/matching', label: 'Buyer Matcher' },
  { to: '/chat', label: 'AI Advisor' },
]

function useAuth() {
  if (typeof window === 'undefined') return { isAuthed: false, email: '' }
  const token = localStorage.getItem('qauto_auth_token')
  const email = localStorage.getItem('qauto_auth_email') || ''
  return { isAuthed: !!token, email }
}

function RequireAuth({ children }: { children: JSX.Element }) {
  const { isAuthed } = useAuth()
  const location = useLocation()
  if (!isAuthed) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return children
}

export default function App() {
  const { isAuthed, email } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    localStorage.removeItem('qauto_auth_token')
    localStorage.removeItem('qauto_auth_email')
    navigate('/login')
  }

  return (
    <div style={{ fontFamily: 'var(--font)', background: 'var(--bg)', minHeight: '100vh', color: 'var(--text)' }}>
      <div
        style={{
          background: 'linear-gradient(135deg, #0f8cf2, #2563eb)',
          borderBottom: '1px solid rgba(15,23,42,0.1)',
          padding: '0 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          height: 60,
          position: 'sticky',
          top: 0,
          zIndex: 100,
          backdropFilter: 'blur(12px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div>
            <div style={{ fontWeight: 900, fontSize: 15, color: '#ffffff', letterSpacing: '0.05em' }}>QAUTO-AI</div>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.8)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
              Used Car Intelligence
            </div>
          </div>
        </div>
        {isAuthed && (
          <div style={{ display: 'flex', gap: 3, flex: 1, justifyContent: 'center' }}>
            {nav.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                style={({ isActive }) => ({
                  padding: '7px 12px',
                  borderRadius: 999,
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                  background: isActive ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.12)',
                  color: isActive ? '#1d4ed8' : '#e0edff',
                  textDecoration: 'none',
                })}
              >
                {label}
              </NavLink>
            ))}
          </div>
        )}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          {isAuthed ? (
            <>
              <div
                style={{
                  fontSize: 11,
                  color: 'rgba(255,255,255,0.9)',
                  padding: '4px 10px',
                  borderRadius: 999,
                  background: 'rgba(15,23,42,0.25)',
                }}
              >
                {email || 'Dealer'}
              </div>
              <button
                onClick={handleLogout}
                style={{
                  fontSize: 11,
                  padding: '6px 12px',
                  borderRadius: 999,
                  border: '1px solid rgba(255,255,255,0.6)',
                  background: 'transparent',
                  color: '#ffffff',
                }}
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <NavLink
                to="/login"
                style={{
                  fontSize: 11,
                  padding: '6px 12px',
                  borderRadius: 999,
                  border: '1px solid rgba(255,255,255,0.6)',
                  background: 'transparent',
                  color: '#ffffff',
                  textDecoration: 'none',
                }}
              >
                Login
              </NavLink>
              <NavLink
                to="/register"
                style={{
                  fontSize: 11,
                  padding: '6px 12px',
                  borderRadius: 999,
                  border: 'none',
                  background: '#ffffff',
                  color: '#1d4ed8',
                  textDecoration: 'none',
                  fontWeight: 700,
                }}
              >
                Register
              </NavLink>
            </>
          )}
        </div>
      </div>

      <div style={{ padding: '22px 24px' }}>
        <Suspense fallback={<DashboardSkeleton />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/"
              element={
                <RequireAuth>
                  <MarketHub />
                </RequireAuth>
              }
            />
            <Route
              path="/inventory"
              element={
                <RequireAuth>
                  <InventoryHealth />
                </RequireAuth>
              }
            />
            <Route
              path="/pricing"
              element={
                <RequireAuth>
                  <PricingTool />
                </RequireAuth>
              }
            />
            <Route
              path="/competitors"
              element={
                <RequireAuth>
                  <CompetitorPrices />
                </RequireAuth>
              }
            />
            <Route
              path="/trends"
              element={
                <RequireAuth>
                  <MarketTrends />
                </RequireAuth>
              }
            />
            <Route
              path="/matching"
              element={
                <RequireAuth>
                  <BuyerMatcher />
                </RequireAuth>
              }
            />
            <Route
              path="/chat"
              element={
                <RequireAuth>
                  <AIAdvisor />
                </RequireAuth>
              }
            />
          </Routes>
        </Suspense>
      </div>
    </div>
  )
}
