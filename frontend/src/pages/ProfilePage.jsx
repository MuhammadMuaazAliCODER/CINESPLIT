import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { changeAccountPassword, updateCurrentUser } from '../services/auth.js'
import AuthCard from '../components/AuthCard.jsx'
import FormField from '../components/FormField.jsx'
import { useNavigate } from 'react-router-dom'

export default function ProfilePage() {
  const { user, setUser, signOut } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState(user.full_name || '')
  const [bio, setBio] = useState(user.bio || '')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', password_confirmation: '' })
  const [passwordNotice, setPasswordNotice] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordBusy, setPasswordBusy] = useState(false)

  async function save(event) {
    event.preventDefault()
    setBusy(true)
    setNotice('')
    setError('')
    try {
      const { data } = await updateCurrentUser({ full_name: fullName, bio })
      setUser(data)
      setNotice('Profile updated.')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Your profile could not be updated.')
    } finally {
      setBusy(false)
    }
  }

  async function updatePassword(event) {
    event.preventDefault()
    setPasswordBusy(true)
    setPasswordNotice('')
    setPasswordError('')
    try {
      await changeAccountPassword(passwordForm)
      setPasswordNotice('Password changed. Please sign in again.')
      await signOut()
      navigate('/login', { replace: true })
    } catch (requestError) {
      setPasswordError(requestError.response?.data?.detail || Object.values(requestError.response?.data?.errors || {}).flat().join(' ') || 'Your password could not be changed.')
    } finally {
      setPasswordBusy(false)
    }
  }

  return (
    <AuthCard eyebrow="YOUR CINESPLIT ACCOUNT" title={user.full_name || user.username} description={user.email}>
      <form className="auth-form" onSubmit={save}>
        <FormField id="username" label="Username" value={user.username} readOnly />
        <FormField id="full_name" label="Full name" maxLength={120} value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <div className="form-field"><label htmlFor="bio">About you</label><textarea id="bio" rows="3" maxLength={500} value={bio} onChange={(e) => setBio(e.target.value)} /></div>
        <p className="profile-meta">Member since {new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long' })}</p>
        {notice && <p className="form-notice" role="status">{notice}</p>}
        {error && <p className="form-alert" role="alert">{error}</p>}
        <button className="primary-button" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</button>
      </form>
      <div className="section-divider" />
      <h2 className="section-title">Change password</h2>
      <form className="auth-form" onSubmit={updatePassword}>
        <FormField id="current_password" label="Current password" type="password" autoComplete="current-password" required value={passwordForm.current_password} onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })} />
        <FormField id="new_password" label="New password" type="password" autoComplete="new-password" minLength={12} required value={passwordForm.new_password} onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })} />
        <FormField id="password_confirmation" label="Confirm new password" type="password" autoComplete="new-password" required value={passwordForm.password_confirmation} onChange={(e) => setPasswordForm({ ...passwordForm, password_confirmation: e.target.value })} />
        {passwordNotice && <p className="form-notice" role="status">{passwordNotice}</p>}
        {passwordError && <p className="form-alert" role="alert">{passwordError}</p>}
        <button className="primary-button" type="submit" disabled={passwordBusy}>{passwordBusy ? 'Changing…' : 'Change password'}</button>
      </form>
    </AuthCard>
  )
}
