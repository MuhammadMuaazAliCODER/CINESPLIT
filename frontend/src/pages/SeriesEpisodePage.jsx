import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faClock } from '@fortawesome/free-solid-svg-icons'
import { getSeriesEpisode, getSeriesDetail } from '../services/series.js'
import { createRequestGuard } from '../features/requestGuard.js'
import VideoPlayer from '../components/VideoPlayer.jsx'
import FavoriteButton from '../components/FavoriteButton.jsx'
import ReviewSection from '../components/ReviewSection.jsx'

export default function SeriesEpisodePage() {
  const { slug, episodeSlug } = useParams()
  const [episode, setEpisode] = useState(null)
  const [series, setSeries] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const request = useRef(null)
  if (!request.current) request.current = createRequestGuard()

  useEffect(() => {
    const token = request.current.begin()
    const controller = new AbortController()
    setError('')
    setLoading(true)
    setEpisode(null)
    setSeries(null)
    Promise.all([
      getSeriesEpisode(slug, episodeSlug, { signal: controller.signal }),
      getSeriesDetail(slug, { signal: controller.signal }),
    ]).then(([episodeResponse, seriesResponse]) => {
      if (!request.current.isCurrent(token)) return
      setEpisode(episodeResponse.data)
      setSeries(seriesResponse.data)
      setError('')
    }).catch((requestError) => {
      if (request.current.isCurrent(token) && requestError.name !== 'CanceledError') {
        setError(requestError.response?.data?.detail || 'Episode could not be loaded.')
      }
    }).finally(() => {
      if (request.current.isCurrent(token)) setLoading(false)
    })
    return () => { controller.abort(); request.current.invalidate() }
  }, [slug, episodeSlug])

  if (loading) return <p role="status" className="movie-state">Loading episode…</p>
  if (error || !episode || !series) return <section><p role="alert" className="movie-state">{error || 'Episode not found.'}</p><Link className="quiet-button" to={`/series/${encodeURIComponent(slug)}`}><FontAwesomeIcon icon={faArrowLeft}/> Back to series</Link></section>
  return <article className="episode-detail"><Link className="quiet-button" to={`/series/${encodeURIComponent(slug)}`}><FontAwesomeIcon icon={faArrowLeft}/> Back to {series.title}</Link><div className="episode-detail-art"><span className="eyebrow">{episode.type === 'special' ? `SPECIAL ${episode.special_number}` : `SEASON EPISODE ${episode.episode_number}`}</span><h1>{episode.title}</h1><p><FontAwesomeIcon icon={faClock}/> {episode.duration} min {episode.release_date && ` · ${episode.release_date}`}</p><p>{episode.description || 'More details for this episode will be available soon.'}</p></div><FavoriteButton contentType="episode" contentId={episode.id}/><VideoPlayer video={episode.video} poster={episode.poster_media} title={episode.title} contentType="episode" contentId={episode.id}/><ReviewSection contentType="episode" contentId={episode.id}/></article>
}
