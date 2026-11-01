import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { getDiscovery } from '../services/engagement.js'
import SeoHead from '../components/SeoHead.jsx'

export default function DiscoverPage() {
  const [params, setParams] = useSearchParams()
  const [term, setTerm] = useState(params.get('q') || '')
  const [filters, setFilters] = useState({ genre: params.get('genre') || '', content_type: params.get('content_type') || '', release_year: params.get('release_year') || '', sort: params.get('sort') || '-release_year' })
  const [data, setData] = useState({ results: [], page: 1, pages: 0, total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => { setTerm(params.get('q') || ''); setFilters({ genre: params.get('genre') || '', content_type: params.get('content_type') || '', release_year: params.get('release_year') || '', sort: params.get('sort') || '-release_year' }) }, [params])
  useEffect(() => {
    let active = true; const controller = new AbortController(); setLoading(true); setError('')
    const query = Object.fromEntries(params.entries()); query.page = query.page || 1; query.page_size = 20
    getDiscovery(query, { signal: controller.signal }).then(({ data: result }) => { if (active) setData(result) }).catch((e) => { if (active && e.name !== 'CanceledError') setError(e.response?.data?.detail || 'Search could not be completed.') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false; controller.abort() }
  }, [params])
  function submit(event) { event.preventDefault(); const next = new URLSearchParams(); if (term.trim()) next.set('q', term.trim()); for (const [key, value] of Object.entries(filters)) if (value) next.set(key, value); setParams(next) }
  function changePage(page) { const next = new URLSearchParams(params); next.set('page', String(page)); setParams(next) }
  return <section className="library-page"><SeoHead title="Search films and series | CineSplit" description="Search CineSplit's published films and series by title, genre, content type, and release year." path="/discover/"/><span className="eyebrow">FIND YOUR NEXT STORY</span><h1>Search & discover</h1><form className="discover-filters" onSubmit={submit}><input aria-label="Search titles and descriptions" placeholder="Search movies and series" value={term} onChange={(e) => setTerm(e.target.value)}/><input aria-label="Genre" placeholder="Genre" value={filters.genre} onChange={(e) => setFilters({ ...filters, genre: e.target.value })}/><select aria-label="Content type" value={filters.content_type} onChange={(e) => setFilters({ ...filters, content_type: e.target.value })}><option value="">Movies and series</option><option value="movie">Movies</option><option value="series">Series</option></select><input aria-label="Release year" type="number" min="1870" max="2100" placeholder="Year" value={filters.release_year} onChange={(e) => setFilters({ ...filters, release_year: e.target.value })}/><select aria-label="Sort results" value={filters.sort} onChange={(e) => setFilters({ ...filters, sort: e.target.value })}><option value="-release_year">Newest release</option><option value="release_year">Oldest release</option><option value="title">Title A–Z</option><option value="-title">Title Z–A</option><option value="-created_at">Recently added</option></select><button className="primary-button">Search</button></form>
    {loading ? <p className="movie-state" role="status">Searching…</p> : error ? <p className="form-alert" role="alert">{error}</p> : !data.results.length ? <p className="movie-state">No published titles match those filters.</p> : <><p className="catalog-results-heading">{data.total} results</p><div className="discovery-grid">{data.results.map((item) => <Link className="discovery-card" to={item.url} key={`${item.content_type}-${item.id}`}><div className="discovery-art">{item.poster_url && <img src={item.poster_url} alt="" loading="lazy"/>}<span>{item.content_type}</span></div><h3>{item.title}</h3><p>{item.release_year} · {item.genres.join(' / ')}</p></Link>)}</div>{data.pages > 1 && <nav className="movie-pagination"><button className="quiet-button" disabled={data.page <= 1} onClick={() => changePage(data.page - 1)}>Previous</button><span>Page {data.page} of {data.pages}</span><button className="quiet-button" disabled={data.page >= data.pages} onClick={() => changePage(data.page + 1)}>Next</button></nav>}</>}
  </section>
}
