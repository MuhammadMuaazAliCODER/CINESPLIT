import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { getWatchHistory } from '../services/engagement.js'

export default function ContinueWatching() {
  const { user } = useAuth()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!user) { setItems([]); setError(''); setLoading(false); return }
    let active = true; setLoading(true)
    getWatchHistory({ page_size: 8, continue_watching: true }).then(({ data }) => { if (active) setItems(data.results) })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Continue Watching could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [user])
  if (!user || (!loading && !items.length && !error)) return null
  return <section className="content-shelf"><div className="catalog-results-heading"><h2>Continue Watching</h2><Link to="/watch-history">Watch history</Link></div>{loading ? <p className="movie-state" role="status">Loading your watch list…</p> : error ? <p className="movie-state" role="alert">{error}</p> : <div className="discovery-grid">{items.map((item) => <Link className="discovery-card" to={item.content.url} key={item.id}><div className="discovery-art">{item.content.poster_url && <img src={item.content.poster_url} alt="" loading="lazy"/>}<span>{item.content.title}</span></div><p>Resume · {Math.floor(item.position / 60)}:{String(Math.floor(item.position % 60)).padStart(2, '0')}</p></Link>)}</div>}</section>
}
