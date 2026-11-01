import { useCallback, useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faStar, faTrash, faPen } from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../context/AuthContext.jsx'
import { Link } from 'react-router-dom'
import { createReview, deleteReview, getReviews, updateReview } from '../services/engagement.js'

export default function ReviewSection({ contentType, contentId }) {
  const { user } = useAuth()
  const [data, setData] = useState({ results: [], average_rating: null, rating_count: 0 })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [rating, setRating] = useState(5)
  const [body, setBody] = useState('')
  const ownReview = data.current_review || data.results.find((item) => item.user_id === user?.id)
  const load = useCallback(async () => {
    setLoading(true)
    try { const { data: result } = await getReviews(contentType, contentId); setData(result); setError('') }
    catch (requestError) { setError(requestError.response?.data?.detail || 'Reviews could not be loaded.') }
    finally { setLoading(false) }
  }, [contentType, contentId, user?.id])
  useEffect(() => { void load() }, [load])
  useEffect(() => { setRating(ownReview?.rating ?? 5); setBody(ownReview?.body ?? '') }, [ownReview?.id])
  async function submit(event) {
    event.preventDefault(); setSaving(true); setError(''); setNotice('')
    try {
      const payload = { rating: Number(rating), body }
      if (ownReview) await updateReview(contentType, contentId, ownReview.id, payload)
      else await createReview(contentType, contentId, payload)
      setNotice('Your review was saved.'); await load()
    } catch (requestError) { setError(requestError.response?.data?.detail || 'Review could not be saved.') }
    finally { setSaving(false) }
  }
  async function remove() {
    setSaving(true); setError('')
    try { await deleteReview(contentType, contentId, ownReview.id); setNotice('Your review was removed.'); await load() }
    catch (requestError) { setError(requestError.response?.data?.detail || 'Review could not be removed.') }
    finally { setSaving(false) }
  }
  return <section className="review-section"><div className="review-heading"><div><span className="eyebrow">COMMUNITY REVIEWS</span><h2>Reviews</h2></div><p><FontAwesomeIcon icon={faStar} /> {data.average_rating ?? '—'} <span>· {data.rating_count} ratings</span></p></div>
    {notice && <p className="form-notice" role="status">{notice}</p>}{error && <p className="form-alert" role="alert">{error}</p>}
    {user ? <form className="review-form" onSubmit={submit}><label>Rating<select value={rating} onChange={(event) => setRating(event.target.value)}>{[5,4,3,2,1].map((n) => <option key={n} value={n}>{n} / 5</option>)}</select></label><label>Your review<textarea maxLength="4000" value={body} onChange={(event) => setBody(event.target.value)} placeholder="Share what you thought…" /></label><div><button className="primary-button" disabled={saving}>{saving ? 'Saving…' : ownReview ? <><FontAwesomeIcon icon={faPen}/> Update review</> : 'Post review'}</button>{ownReview && <button type="button" className="quiet-button" disabled={saving} onClick={() => void remove()}><FontAwesomeIcon icon={faTrash}/> Delete</button>}</div></form> : <Link className="quiet-button" to="/login">Sign in to leave a review</Link>}
    {loading ? <p className="movie-state" role="status">Loading reviews…</p> : !data.results.length ? <p className="movie-state">No reviews yet. Be the first to rate it.</p> : <div className="review-list">{data.results.map((item) => <article className="review-card" key={item.id}><div><strong>{item.username}</strong><span><FontAwesomeIcon icon={faStar}/> {item.rating} / 5</span></div><p>{item.body || 'Rated without a written review.'}</p></article>)}</div>}
  </section>
}
