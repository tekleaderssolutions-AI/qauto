import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password || !confirm) {
      setError('Please fill in all fields.')
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    // Simulate registration; in real app, call backend API.
    localStorage.setItem('qauto_auth_token', 'dummy-token')
    localStorage.setItem('qauto_auth_email', email)
    navigate('/')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
      <div className="card" style={{ width: 380, boxShadow: '0 14px 45px rgba(15,23,42,0.08)', background: 'var(--surface)' }}>
        <div style={{ marginBottom: 18, textAlign: 'center' }}>
          <div style={{ fontSize: 26, fontWeight: 900, color: 'var(--accent)', marginBottom: 4 }}>Create QAUTO Account</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Register once to unlock the dashboards</div>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              style={{ marginTop: 4, width: '100%' }}
            />
          </label>
          <label style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              style={{ marginTop: 4, width: '100%' }}
            />
          </label>
          <label style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>
            Confirm password
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Re-enter password"
              style={{ marginTop: 4, width: '100%' }}
            />
          </label>
          {error && <div style={{ fontSize: 11, color: 'var(--danger)' }}>{error}</div>}
          <button type="submit" className="btn-primary" style={{ marginTop: 4 }}>
            Create account
          </button>
        </form>
        <div style={{ marginTop: 14, fontSize: 12, color: 'var(--dim)', textAlign: 'center' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--accent)' }}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}

