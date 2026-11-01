import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faClock, faEarthAmericas, faFilm } from '@fortawesome/free-solid-svg-icons'
import { Link, useParams } from 'react-router-dom'
import { getMovie } from '../services/movies.js'
import { getPublicChapters } from '../services/chapters.js'
import VideoPlayer from '../components/VideoPlayer.jsx'
import FavoriteButton from '../components/FavoriteButton.jsx'
import ReviewSection from '../components/ReviewSection.jsx'
import SeoHead from '../components/SeoHead.jsx'

export default function MovieDetailPage() {
  const { slug } = useParams()
  const [movie, setMovie] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [chapters, setChapters] = useState([])
  const [chaptersError, setChaptersError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setChapters([])
    setChaptersError('')
    getMovie(slug, { signal: controller.signal })
      .then(async ({ data }) => {
        setMovie(data)
        try { const chapterResponse = await getPublicChapters(slug, { signal: controller.signal }); setChapters(chapterResponse.data) }
        catch (requestError) { if (requestError.name !== 'CanceledError') setChaptersError(requestError.response?.data?.detail || 'Chapters could not be loaded.') }
      })
      .catch((requestError) => { if (requestError.name !== 'CanceledError') setError(requestError.response?.data?.detail || 'This film could not be found.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [slug])

  if (loading) return <><SeoHead title="Film details | CineSplit" noIndex/><section className="movie-detail-state" role="status">Loading film…</section></>
  if (error || !movie) return <><SeoHead title="Film not found | CineSplit" noIndex/><section className="movie-detail-state" role="alert"><p>{error || 'This film could not be found.'}</p><Link className="quiet-button" to="/">Back to the collection</Link></section></>

  const seoDescription = movie.short_description || movie.description || `Explore ${movie.title} on CineSplit.`
  const movieSchema = {
    '@context': 'https://schema.org',
    '@type': 'Movie',
    name: movie.title,
    description: seoDescription,
    ...(movie.poster_url ? { image: movie.poster_url } : {}),
    ...(movie.genres?.length ? { genre: movie.genres } : {}),
    ...(movie.duration_minutes ? { duration: `PT${movie.duration_minutes}M` } : {}),
    ...(movie.original_language ? { inLanguage: movie.original_language } : {}),
    ...(movie.director ? { director: { '@type': 'Person', name: movie.director } } : {}),
    ...(movie.cast?.length ? { actor: movie.cast.map((name) => ({ '@type': 'Person', name })) } : {}),
    ...(movie.content_rating ? { contentRating: movie.content_rating } : {}),
  }
  const siteUrl = (import.meta.env.VITE_PUBLIC_SITE_URL || '').replace(/\/+$/, '')
  const breadcrumbSchema = siteUrl ? {
    '@context': 'https://schema.org', '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Films', item: `${siteUrl}/` },
      { '@type': 'ListItem', position: 2, name: movie.title, item: `${siteUrl}/movies/${movie.slug}/` },
    ],
  } : null

  return (
    <article className="movie-detail-page">
      <SeoHead title={`${movie.title} (${movie.release_year}) | CineSplit`} description={seoDescription} path={`/movies/${movie.slug}/`} image={movie.poster_url} type="video.movie" schema={[movieSchema, breadcrumbSchema]} noIndex={seoDescription.trim().length < 40} />
      <Link to="/" className="back-link"><FontAwesomeIcon icon={faArrowLeft} aria-hidden="true" /> Back to collection</Link>
      <div className="movie-detail-art">
        {movie.backdrop_url && <img className="movie-detail-backdrop" src={movie.backdrop_url} alt="" aria-hidden="true" />}
        {movie.poster_url ? <img className="movie-detail-poster" src={movie.poster_url} alt={`${movie.title} poster`} width="190" height="266" loading="eager" fetchPriority="high" /> : <div className="movie-detail-poster detail-poster-placeholder"><FontAwesomeIcon icon={faFilm} aria-hidden="true" /></div>}
        <div className="movie-detail-heading"><span className="eyebrow">CINESPLIT ORIGINAL COLLECTION</span><h1>{movie.title}</h1><p>{movie.short_description}</p><div className="detail-facts"><span>{movie.release_year}</span><span>{movie.content_rating}</span><span><FontAwesomeIcon icon={faClock} aria-hidden="true" /> {movie.duration_minutes} min</span><span><FontAwesomeIcon icon={faEarthAmericas} aria-hidden="true" /> {movie.original_language}</span></div></div>
      </div>
      <FavoriteButton contentType="movie" contentId={movie.id}/>
      <div className="movie-detail-content">
        <section><span className="eyebrow">THE STORY</span><p>{movie.description}</p></section>
        <dl className="movie-facts">
          <div><dt>Genres</dt><dd>{movie.genres.map((genre) => genre.replace(/\b\w/g, (letter) => letter.toUpperCase())).join(', ')}</dd></div>
          <div><dt>Director</dt><dd>{movie.director}</dd></div>
          <div><dt>Cast</dt><dd>{movie.cast.length ? movie.cast.join(', ') : '—'}</dd></div>
          <div><dt>Production</dt><dd>{movie.production_company}</dd></div>
          <div><dt>Country</dt><dd>{movie.country}</dd></div>
        </dl>
      </div>
      {movie.video?.secure_url && <VideoPlayer video={movie.video} poster={movie.poster_media} title={movie.title} contentType="movie" contentId={movie.id} />}
      <ReviewSection contentType="movie" contentId={movie.id}/>
      <section className="public-chapters" aria-labelledby="chapters-title">
        <div className="chapter-section-heading"><div><span className="eyebrow">THE STORY, IN CHAPTERS</span><h2 id="chapters-title">Chapters</h2><p>Published chapters for this film.</p></div></div>
        {chaptersError ? <p className="movie-state" role="alert">{chaptersError}</p> : chapters.length ? <ol className="public-chapter-list">{chapters.map((chapter) => <li className="public-chapter-card" key={chapter.id}><Link to={`/movies/${encodeURIComponent(slug)}/chapters/${encodeURIComponent(chapter.slug)}`} className="public-chapter-link"><span className="chapter-number">{chapter.chapter_number}</span><div><h3>{chapter.title}</h3>{chapter.description && <p>{chapter.description}</p>}<span className="chapter-meta">{chapter.duration} min · {chapter.is_free ? 'Available without restrictions' : 'Availability restricted'}</span></div><span>{chapter.video ? 'Watch chapter' : 'Chapter details'}</span></Link></li>)}</ol> : <p className="movie-state">No published chapters are available yet.</p>}
      </section>
    </article>
  )
}
