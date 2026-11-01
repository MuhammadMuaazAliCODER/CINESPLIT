import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getFeaturedContent, getLatestContent } from '../services/engagement.js'

function Shelf({ title, items }) {
  if (!items.length) return null
  return <section className="content-shelf"><div className="catalog-results-heading"><h2>{title}</h2><Link to="/discover">Explore all</Link></div><div className="discovery-grid">{items.map((item) => <Link className="discovery-card" to={item.url} key={`${item.content_type}-${item.id}`}><div className="discovery-art">{item.poster_url && <img src={item.poster_url} alt={`${item.title} poster`} loading="lazy"/>}<span>{item.content_type === 'series' ? 'Series' : 'Film'}</span></div><h3>{item.title}</h3><p>{item.release_year} · {item.genres.join(' / ')}</p></Link>)}</div></section>
}

export default function DiscoveryShelves() {
  const [featured, setFeatured] = useState([])
  const [latest, setLatest] = useState([])
  useEffect(() => {
    let active = true
    Promise.all([getFeaturedContent(), getLatestContent()]).then(([a, b]) => { if (active) { setFeatured(a.data.results); setLatest(b.data.results) } }).catch(() => {})
    return () => { active = false }
  }, [])
  return <><Shelf title="Featured stories" items={featured}/><Shelf title="Latest releases" items={latest}/></>
}
