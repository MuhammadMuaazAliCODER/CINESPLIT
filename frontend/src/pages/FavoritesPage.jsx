import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getFavorites } from '../services/engagement.js'

export default function FavoritesPage() {
  const [data, setData] = useState({ results: [], page: 1, pages: 0, total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  useEffect(() => { let active = true; setLoading(true); getFavorites({ page, page_size: 20 }).then(({ data: result }) => { if (active) { setData(result); setError('') } }).catch((e) => { if (active) setError(e.response?.data?.detail || 'Favorites could not be loaded.') }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [page])
  return <section className="library-page"><span className="eyebrow">YOUR LIBRARY</span><h1>Favorites</h1>{loading ? <p role="status" className="movie-state">Loading favorites…</p> : error ? <p role="alert" className="form-alert">{error}</p> : !data.results.length ? <p className="movie-state">Your favorites will appear here. Save films, series, chapters, or episodes as you explore.</p> : <><div className="discovery-grid">{data.results.map((item) => <Link className="discovery-card" to={item.url} key={`${item.content_type}-${item.content_id}`}><div className="discovery-art">{item.poster_url && <img src={item.poster_url} alt="" loading="lazy"/>}<span>{item.content_type}</span></div><h3>{item.title}</h3><p>{item.release_year}</p></Link>)}</div>{data.pages > 1 && <nav className="movie-pagination"><button className="quiet-button" disabled={loading || page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {data.page} of {data.pages}</span><button className="quiet-button" disabled={loading || page >= data.pages} onClick={() => setPage((value) => value + 1)}>Next</button></nav>}</>}</section>
}
