import { useCallback, useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTrash } from '@fortawesome/free-solid-svg-icons'
import { Link } from 'react-router-dom'
import { getWatchHistory, removeWatchHistory } from '../services/engagement.js'
import { useSearchParams } from 'react-router-dom'

export default function WatchHistoryPage({ continueOnly = false }) {
  const [searchParams] = useSearchParams()
  const continueMode = continueOnly || searchParams.get('continue') === '1'
  const [data, setData] = useState({ results: [], page: 1, pages: 0, total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const load = useCallback(async () => { setLoading(true); try { const { data: result } = await getWatchHistory({ page, page_size: 20, ...(continueMode ? { continue_watching: true } : {}) }); setData(result); setError('') } catch (e) { setError(e.response?.data?.detail || 'Watch history could not be loaded.') } finally { setLoading(false) } }, [continueMode, page])
  useEffect(() => { void load() }, [load])
  async function remove(item) { try { await removeWatchHistory(item.content_type, item.content_id); await load() } catch (e) { setError(e.response?.data?.detail || 'History item could not be removed.') } }
  return <section className="library-page"><span className="eyebrow">YOUR ACTIVITY</span><h1>{continueMode ? 'Continue Watching' : 'Watch history'}</h1>{error && <p role="alert" className="form-alert">{error}</p>}{loading ? <p role="status" className="movie-state">Loading watch history…</p> : !data.results.length ? <p className="movie-state">{continueMode ? 'You are all caught up. Start a film or episode to find it here.' : 'Nothing watched yet. Your playback history will appear here.'}</p> : <><div className="history-list">{data.results.map((item) => <article className="history-row" key={item.id}><Link to={item.content.url} className="history-content"><div className="discovery-art">{item.content.poster_url && <img src={item.content.poster_url} alt="" loading="lazy"/>}</div><div><span className="eyebrow">{item.content_type} · {item.completed ? 'Completed' : 'In progress'}</span><h2>{item.content.title}</h2><p>{Math.floor(item.position / 60)}:{String(Math.floor(item.position % 60)).padStart(2, '0')} {item.duration ? `/ ${Math.floor(item.duration / 60)}:${String(Math.floor(item.duration % 60)).padStart(2, '0')}` : ''}</p></div></Link><button className="icon-button danger-icon" aria-label={`Remove ${item.content.title} from history`} onClick={() => void remove(item)}><FontAwesomeIcon icon={faTrash}/></button></article>)}</div>{data.pages > 1 && <nav className="movie-pagination"><button className="quiet-button" disabled={loading || page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {data.page} of {data.pages}</span><button className="quiet-button" disabled={loading || page >= data.pages} onClick={() => setPage((value) => value + 1)}>Next</button></nav>}</>}</section>
}
