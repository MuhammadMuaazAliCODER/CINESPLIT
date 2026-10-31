import { useCallback, useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faArrowRight, faPen, faStar, faTrash } from '@fortawesome/free-solid-svg-icons'
import { Link } from 'react-router-dom'
import MovieEditor from '../components/MovieEditor.jsx'
import ChapterManagement from '../components/ChapterManagement.jsx'
import { createAdminMovie, deleteAdminMovie, getAdminMovies, updateAdminMovie } from '../services/movies.js'

export default function AdminMoviesPage() {
  const [pageData, setPageData] = useState({ results: [], page: 1, page_size: 20, pages: 0, total: 0 })
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [editing, setEditing] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadMovies = useCallback((signal) => {
    setLoading(true)
    const params = { page, page_size: 20, sort: '-created_at' }
    if (statusFilter) params.status = statusFilter
    getAdminMovies(params, { signal })
      .then(({ data }) => setPageData(data))
      .catch((requestError) => { if (requestError.name !== 'CanceledError') setError(requestError.response?.data?.detail || 'Movies could not be loaded.') })
      .finally(() => { if (!signal?.aborted) setLoading(false) })
  }, [page, statusFilter])

  useEffect(() => {
    const controller = new AbortController()
    setError('')
    loadMovies(controller.signal)
    return () => controller.abort()
  }, [loadMovies])

  async function saveMovie(data) {
    setSaving(true); setError(''); setNotice('')
    try {
      if (editing) await updateAdminMovie(editing.id, data)
      else await createAdminMovie(data)
      setEditing(null)
      setNotice(editing ? 'Movie updated.' : 'Movie created.')
      const controller = new AbortController()
      loadMovies(controller.signal)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || Object.values(requestError.response?.data?.errors || {}).flat().join(' ') || 'Movie could not be saved.')
    } finally { setSaving(false) }
  }

  async function toggleMovie(movie, field, value) {
    setError(''); setNotice('')
    try {
      await updateAdminMovie(movie.id, { [field]: value })
      setNotice(field === 'status' ? (value === 'published' ? 'Movie published.' : 'Movie moved to drafts.') : 'Featured status updated.')
      const controller = new AbortController()
      loadMovies(controller.signal)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Movie could not be updated.')
    }
  }

  async function removeMovie(movie) {
    if (!window.confirm(`Delete “${movie.title}”? This action cannot be undone.`)) return
    setError(''); setNotice('')
    try {
      await deleteAdminMovie(movie.id, movie.slug)
      setNotice('Movie deleted.')
      const controller = new AbortController()
      loadMovies(controller.signal)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Movie could not be deleted.')
    }
  }

  return (
    <section className="admin-movies-page" aria-labelledby="admin-movies-title">
      <div className="admin-page-heading"><div><span className="eyebrow">CINESPLIT · STUDIO</span><h1 id="admin-movies-title">Movie management</h1><p>Shape the collection, one story at a time.</p></div><Link className="quiet-button" to="/">View public catalog <FontAwesomeIcon icon={faArrowRight} aria-hidden="true" /></Link></div>
      {notice && <p className="form-notice" role="status">{notice}</p>}
      {error && <p className="form-alert" role="alert">{error}</p>}
      <MovieEditor movie={editing} saving={saving} error="" onSubmit={saveMovie} onCancel={() => setEditing(null)} />
      {editing && <ChapterManagement key={editing.id} movie={editing} />}

      <section className="admin-movie-list" aria-labelledby="admin-list-title">
        <div className="admin-list-heading"><div><span className="eyebrow">LIBRARY</span><h2 id="admin-list-title">All films <span className="admin-count">{pageData.total}</span></h2></div><label className="admin-status-filter">Show<select value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1) }}><option value="">All statuses</option><option value="draft">Drafts</option><option value="published">Published</option></select></label></div>
        {loading ? <p className="movie-state" role="status">Loading library…</p> : !pageData.results.length ? <p className="movie-state">No movies in this view yet.</p> : <div className="admin-movie-table-wrap"><table className="admin-movie-table"><thead><tr><th>Film</th><th>Release</th><th>Status</th><th>Featured</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{pageData.results.map((movie) => <tr key={movie.id}>
          <td><strong>{movie.title}</strong><small>{movie.slug}</small></td><td>{movie.release_year}</td><td><span className={`movie-status status-${movie.status}`}>{movie.status}</span></td><td>{movie.is_featured ? 'Yes' : 'No'}</td>
          <td className="admin-row-actions"><button type="button" className="icon-button" aria-label={`Edit ${movie.title}`} onClick={() => { setEditing(movie); setError('') }}><FontAwesomeIcon icon={faPen} aria-hidden="true" /></button><button type="button" className="icon-button" aria-label={`${movie.is_featured ? 'Unfeature' : 'Feature'} ${movie.title}`} onClick={() => void toggleMovie(movie, 'is_featured', !movie.is_featured)}><FontAwesomeIcon icon={faStar} aria-hidden="true" /></button><button type="button" className="icon-button" aria-label={`${movie.status === 'published' ? 'Unpublish' : 'Publish'} ${movie.title}`} onClick={() => void toggleMovie(movie, 'status', movie.status === 'published' ? 'draft' : 'published')}>{movie.status === 'published' ? 'Unpublish' : 'Publish'}</button><button type="button" className="icon-button danger-icon" aria-label={`Delete ${movie.title}`} onClick={() => void removeMovie(movie)}><FontAwesomeIcon icon={faTrash} aria-hidden="true" /></button></td>
        </tr>)}</tbody></table></div>}
        {pageData.pages > 1 && <nav className="movie-pagination" aria-label="Admin movie pages"><button className="quiet-button" type="button" disabled={loading || page <= 1} onClick={() => setPage((value) => value - 1)}><FontAwesomeIcon icon={faArrowLeft} aria-hidden="true" /> Previous</button><span>Page {pageData.page} of {pageData.pages}</span><button className="quiet-button" type="button" disabled={loading || page >= pageData.pages} onClick={() => setPage((value) => value + 1)}>Next <FontAwesomeIcon icon={faArrowRight} aria-hidden="true" /></button></nav>}
      </section>
    </section>
  )
}
