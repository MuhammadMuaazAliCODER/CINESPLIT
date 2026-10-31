import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowRight, faRotate } from '@fortawesome/free-solid-svg-icons'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import AuthCard from '../components/AuthCard.jsx'
import FormField from '../components/FormField.jsx'
import { resendVerification, verifyEmail } from '../services/auth.js'

function messageFrom(error) {
  const data = error.response?.data
  if (data?.errors) return Object.values(data.errors).flat().join(' ')
  return data?.detail || 'We could not verify this code. Please try again.'
}

export default function VerifyEmailPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const email = params.get('email') || ''
  const [emailEntry, setEmailEntry] = useState(email)
  const initialCooldown = params.get('cooldown') === '1' ? 60 : 0
  const [code, setCode] = useState('')
  const [secondsLeft, setSecondsLeft] = useState(initialCooldown)
  const [busy, setBusy] = useState(false)
  const [resending, setResending] = useState(false)
  const [notice, setNotice] = useState(params.get('delivery') === 'failed' ? 'Your account was created, but the email could not be delivered. Request a new code when the cooldown ends.' : '')
  const [error, setError] = useState('')

  useEffect(() => {
    if (secondsLeft <= 0) return undefined
    const timer = window.setTimeout(() => setSecondsLeft((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearTimeout(timer)
  }, [secondsLeft])

  async function submit(event) {
    event.preventDefault()
    if (!/^\d{6}$/.test(code) || busy) return
    setBusy(true)
    setError('')
    try {
      await verifyEmail({ email: email || emailEntry, code })
      navigate('/login', { replace: true, state: { message: 'Email verified. Sign in to continue.' } })
    } catch (requestError) {
      setError(messageFrom(requestError))
    } finally {
      setBusy(false)
    }
  }

  async function resend() {
    if (secondsLeft > 0 || resending || !(email || emailEntry)) return
    setResending(true)
    setError('')
    setNotice('')
    try {
      const { data } = await resendVerification({ email: email || emailEntry })
      setNotice(data.detail)
      setSecondsLeft(60)
    } catch (requestError) {
      setError(messageFrom(requestError))
    } finally {
      setResending(false)
    }
  }

  return (
    <AuthCard title="Check your inbox." description={email ? <>Enter the six-digit code sent to <strong className="email-emphasis">{email}</strong>. It expires in 10 minutes.</> : 'Enter the email address used to create your account.'}
      footer={<>Already verified? <Link to="/login">Sign in</Link></>}>
      <form className="auth-form" onSubmit={submit} noValidate>
        {!email && <FormField id="email" label="Email address" type="email" autoComplete="email" required value={emailEntry} onChange={(e) => setEmailEntry(e.target.value)} />}
        <FormField id="code" label="Six-digit code" type="text" inputMode="numeric" pattern="[0-9]{6}" autoComplete="one-time-code" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />
        {notice && <p className="form-notice" role="status">{notice}</p>}
        {error && <p className="form-alert" role="alert">{error}</p>}
        <button className="primary-button" type="submit" disabled={busy || code.length !== 6 || !(email || emailEntry)}>{busy ? 'Verifying…' : <>Verify email <FontAwesomeIcon icon={faArrowRight} aria-hidden="true" /></>}</button>
      </form>
      <button className="text-button resend-button" type="button" onClick={resend} disabled={!(email || emailEntry) || secondsLeft > 0 || resending}>
        <FontAwesomeIcon icon={faRotate} aria-hidden="true" />
        {resending ? 'Sending…' : secondsLeft ? `Resend available in ${secondsLeft}s` : 'Resend verification code'}
      </button>
    </AuthCard>
  )
}
