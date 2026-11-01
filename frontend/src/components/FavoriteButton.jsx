import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHeart } from '@fortawesome/free-solid-svg-icons'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { addFavorite, getFavoriteState, removeFavorite } from '../services/engagement.js'

export default function FavoriteButton({ contentType, contentId, compact = false }) {
  const { user, loading } = useAuth()
  const [favorited, setFavorited] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let current = true
    if (user && contentId) getFavoriteState(contentType, contentId).then(({ data }) => { if (current) setFavorited(data.favorited) }).catch(() => { if (current) setError('Favorites could not be loaded.') })
    return () => { current = false }
  }, [user, contentType, contentId])
  if (loading) return compact ? null : <span className="quiet-button" role="status">Loading account…</span>
  if (!user) return <Link className={compact ? 'favorite-card-button' : 'quiet-button'} to="/login" aria-label="Sign in to save as a favorite" title="Sign in to save"><FontAwesomeIcon icon={faHeart}/>{!compact && ' Sign in to save'}</Link>
  async function toggle() {
    setBusy(true); setError('')
    try {
      if (favorited) await removeFavorite(contentType, contentId)
      else await addFavorite(contentType, contentId)
      setFavorited(!favorited)
    } catch (requestError) { setError(requestError.response?.data?.detail || 'Favorite could not be updated.') }
    finally { setBusy(false) }
  }
  return <div className={compact ? 'favorite-control favorite-control-compact' : 'favorite-control'}><button className={compact ? 'favorite-card-button' : 'quiet-button'} type="button" disabled={busy} aria-pressed={favorited} aria-label={favorited ? 'Remove favorite' : 'Add to favorites'} onClick={() => void toggle()}><FontAwesomeIcon icon={faHeart} />{!compact && ` ${busy ? 'Saving…' : favorited ? 'Remove favorite' : 'Add to favorites'}`}</button>{error && <span role="alert">{error}</span>}</div>
}
