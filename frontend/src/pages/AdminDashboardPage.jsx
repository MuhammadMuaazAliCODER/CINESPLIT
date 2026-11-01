import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faChartLine, faFilm, faLayerGroup, faPhotoFilm, faTv, faUsers, faStar, faFolderOpen } from '@fortawesome/free-solid-svg-icons'
import { Link } from 'react-router-dom'
import { getDashboard } from '../services/engagement.js'

const tiles = [["users", "Registered users", faUsers], ["movies", "Movies", faFilm], ["series", "Series", faTv], ["seasons", "Seasons", faLayerGroup], ["episodes", "Episodes", faPhotoFilm], ["media_assets", "Media assets", faPhotoFilm], ["media_cleanup_pending", "Media cleanup pending", faPhotoFilm], ["published", "Published records", faChartLine], ["drafts", "Draft records", faFolderOpen], ["reviews", "Reviews", faStar]]

export default function AdminDashboardPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => { let active = true; getDashboard().then(({ data: result }) => { if (active) setData(result) }).catch((e) => { if (active) setError(e.response?.data?.detail || 'Dashboard could not be loaded.') }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [])
  return <section className="library-page admin-dashboard"><span className="eyebrow">CINESPLIT · STUDIO</span><h1>Overview</h1>{error && <p className="form-alert" role="alert">{error}</p>}{loading ? <p className="movie-state" role="status">Loading dashboard…</p> : data && <><div className="dashboard-grid">{tiles.map(([key, label, icon]) => <article className="dashboard-tile" key={key}><FontAwesomeIcon icon={icon}/><span>{label}</span><strong>{data.counts[key].toLocaleString()}</strong></article>)}</div><div className="dashboard-columns"><section className="admin-movie-list"><h2>Recent registrations</h2>{!data.recent_users.length ? <p className="movie-state">No registrations yet.</p> : data.recent_users.map((user) => <p className="dashboard-activity" key={user.id}><strong>{user.username}</strong><time>{new Date(user.created_at).toLocaleDateString()}</time></p>)}</section><section className="admin-movie-list"><h2>Recent content</h2>{!data.recent_content.length ? <p className="movie-state">No content has been added yet.</p> : data.recent_content.map((item, index) => <p className="dashboard-activity" key={`${item.type}-${item.created_at}-${index}`}><strong>{item.title || item.type}</strong><span>{item.type}</span></p>)}</section></div></>}
    <nav className="dashboard-links" aria-label="Studio management"><Link className="quiet-button" to="/admin/movies">Manage movies & chapters</Link><Link className="quiet-button" to="/admin/series">Manage series & episodes</Link><Link className="quiet-button" to="/admin/media">Media library</Link></nav>
  </section>
}
