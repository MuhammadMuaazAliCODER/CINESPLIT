import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faClock } from '@fortawesome/free-solid-svg-icons'
import { Link, useParams } from 'react-router-dom'
import { getPublicChapter } from '../services/chapters.js'
import { getMovie } from '../services/movies.js'
import VideoPlayer from '../components/VideoPlayer.jsx'
import FavoriteButton from '../components/FavoriteButton.jsx'
import ReviewSection from '../components/ReviewSection.jsx'
import SeoHead from '../components/SeoHead.jsx'

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
  if (loading) return <><SeoHead title="Film chapter | CineSplit" noIndex/><p className="movie-state" role="status">Loading chapter…</p></>
  if (error || !chapter || !movie) return <><SeoHead title="Chapter not found | CineSplit" noIndex/><section><p className="movie-state" role="alert">{error || 'Chapter not found.'}</p><Link className="quiet-button" to={`/movies/${encodeURIComponent(slug)}`}>Back to film</Link></section></>
  const seoDescription = chapter.description || `${chapter.title}, chapter ${chapter.chapter_number} of ${movie.title}.`
  const chapterSchema = {
    '@context': 'https://schema.org',
    '@type': 'CreativeWork',
    name: chapter.title,
    description: seoDescription,
    ...(chapter.duration ? { timeRequired: `PT${chapter.duration}M` } : {}),
    isPartOf: { '@type': 'Movie', name: movie.title },
  }
  const siteUrl = (import.meta.env.VITE_PUBLIC_SITE_URL || '').replace(/\/+$/, '')
  const breadcrumbSchema = siteUrl ? {
    '@context': 'https://schema.org', '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Films', item: `${siteUrl}/` },
      { '@type': 'ListItem', position: 2, name: movie.title, item: `${siteUrl}/movies/${movie.slug}/` },
      { '@type': 'ListItem', position: 3, name: chapter.title, item: `${siteUrl}/movies/${movie.slug}/chapters/${chapter.slug}/` },
    ],
  } : null
  return <article className="episode-detail"><SeoHead title={`Chapter ${chapter.chapter_number}: ${chapter.title} | ${movie.title} | CineSplit`} description={seoDescription} path={`/movies/${movie.slug}/chapters/${chapter.slug}/`} image={chapter.poster_media?.secure_url || movie.poster_url} schema={[chapterSchema, breadcrumbSchema]} noIndex={String(chapter.description || '').trim().length < 40}/><Link className="quiet-button" to={`/movies/${encodeURIComponent(slug)}`}><FontAwesomeIcon icon={faArrowLeft}/> Back to {movie.title}</Link><div className="episode-detail-art"><span className="eyebrow">CHAPTER {chapter.chapter_number}</span><h1>{chapter.title}</h1><p><FontAwesomeIcon icon={faClock}/> {chapter.duration} min</p><p>{chapter.description}</p></div><FavoriteButton contentType="chapter" contentId={chapter.id}/><VideoPlayer video={chapter.video} poster={chapter.poster_media} title={chapter.title} contentType="chapter" contentId={chapter.id}/><ReviewSection contentType="chapter" contentId={chapter.id}/></article>
}
