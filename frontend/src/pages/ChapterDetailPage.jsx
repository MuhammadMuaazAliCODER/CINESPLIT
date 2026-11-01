import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faClock } from '@fortawesome/free-solid-svg-icons'
import { Link, useParams } from 'react-router-dom'
import { getPublicChapter } from '../services/chapters.js'
import { getMovie } from '../services/movies.js'
import VideoPlayer from '../components/VideoPlayer.jsx'
import FavoriteButton from '../components/FavoriteButton.jsx'
import ReviewSection from '../components/ReviewSection.jsx'

export default function ChapterDetailPage() {
  const { slug, chapterSlug } = useParams()
  const [chapter, setChapter] = useState(null)
  const [movie, setMovie] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setChapter(null); setMovie(null); setError(''); setLoading(true)
    Promise.all([getPublicChapter(slug, chapterSlug, { signal: controller.signal }), getMovie(slug, { signal: controller.signal })])
      .then(([chapterResponse, movieResponse]) => { if (!controller.signal.aborted) { setChapter(chapterResponse.data); setMovie(movieResponse.data); setError('') } })
      .catch((requestError) => { if (!controller.signal.aborted && requestError.name !== 'CanceledError') setError(requestError.response?.data?.detail || 'Chapter could not be loaded.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [slug, chapterSlug])
  if (loading) return <p className="movie-state" role="status">Loading chapter…</p>
  if (error || !chapter || !movie) return <section><p className="movie-state" role="alert">{error || 'Chapter not found.'}</p><Link className="quiet-button" to={`/movies/${encodeURIComponent(slug)}`}>Back to film</Link></section>
  return <article className="episode-detail"><Link className="quiet-button" to={`/movies/${encodeURIComponent(slug)}`}><FontAwesomeIcon icon={faArrowLeft}/> Back to {movie.title}</Link><div className="episode-detail-art"><span className="eyebrow">CHAPTER {chapter.chapter_number}</span><h1>{chapter.title}</h1><p><FontAwesomeIcon icon={faClock}/> {chapter.duration} min</p><p>{chapter.description}</p></div><FavoriteButton contentType="chapter" contentId={chapter.id}/><VideoPlayer video={chapter.video} poster={chapter.poster_media} title={chapter.title} contentType="chapter" contentId={chapter.id}/><ReviewSection contentType="chapter" contentId={chapter.id}/></article>
}
