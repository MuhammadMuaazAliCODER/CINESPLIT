import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AuthCard from '../components/AuthCard.jsx'
import FormField from '../components/FormField.jsx'
import { useAuth } from '../context/AuthContext.jsx'

export default function LoginPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState(location.state?.message || '')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await signIn({ email, password })
      navigate(location.state?.from?.pathname || '/profile', { replace: true })
    } catch (requestError) {
      const data = requestError.response?.data
      if (data?.code === 'email_not_verified') {
        navigate(`/verify-email?email=${encodeURIComponent(email.trim().toLowerCase())}`, { replace: true })
        return
      }
      setError(data?.detail || 'We could not sign you in. Check your details and try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthCard title="Welcome back." description="Sign in and pick up where the story left off."
      footer={<>New to CineSplit? <Link to="/register">Create an account</Link></>}>
      <form className="auth-form" onSubmit={submit}>
        <FormField id="email" label="Email address" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <FormField id="password" label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        {notice && <p className="form-notice" role="status">{notice}</p>}
        {error && <p className="form-alert" role="alert">{error}</p>}
        <button className="primary-button" type="submit" disabled={busy || !email || !password}>{busy ? 'Signing in…' : <>Sign in <FontAwesomeIcon icon={faArrowRight} aria-hidden="true" /></>}</button>
      </form>
    </AuthCard>
  )
}
