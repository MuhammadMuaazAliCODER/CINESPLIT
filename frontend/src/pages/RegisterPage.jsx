import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'
import { Link, useNavigate } from 'react-router-dom'
import AuthCard from '../components/AuthCard.jsx'
import FormField from '../components/FormField.jsx'
import { registerAccount } from '../services/auth.js'

function errorMessage(error) {
  const data = error.response?.data
  if (data?.errors) return Object.entries(data.errors).map(([key, messages]) => `${key.replaceAll('_', ' ')}: ${[].concat(messages).join(' ')}`).join(' ')
  return data?.detail || 'We could not create your account. Please try again.'
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '', password_confirmation: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await registerAccount(form)
      navigate(`/verify-email?email=${encodeURIComponent(form.email.trim().toLowerCase())}&cooldown=1`)
    } catch (requestError) {
      if (requestError.response?.data?.code === 'email_delivery_failed') {
        navigate(`/verify-email?email=${encodeURIComponent(form.email.trim().toLowerCase())}&cooldown=1&delivery=failed`)
        return
      }
      setError(errorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthCard title="Join the story." description="Create your CineSplit account to make every chapter your own."
      footer={<>Already have an account? <Link to="/login">Sign in</Link></>}>
      <form className="auth-form" onSubmit={submit} noValidate>
        <FormField id="username" label="Username" autoComplete="username" minLength={3} maxLength={30} required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        <FormField id="email" label="Email address" type="email" autoComplete="email" maxLength={254} required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <FormField id="password" label="Password" type="password" autoComplete="new-password" minLength={12} required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <FormField id="password_confirmation" label="Confirm password" type="password" autoComplete="new-password" required value={form.password_confirmation} onChange={(e) => setForm({ ...form, password_confirmation: e.target.value })} />
        {error && <p className="form-alert" role="alert">{error}</p>}
        <button className="primary-button" type="submit" disabled={busy}>{busy ? 'Creating account…' : <>Create account <FontAwesomeIcon icon={faArrowRight} aria-hidden="true" /></>}</button>
      </form>
    </AuthCard>
  )
}
