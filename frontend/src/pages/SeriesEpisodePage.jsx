import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faClock } from '@fortawesome/free-solid-svg-icons'
import { getSeriesEpisode, getSeriesDetail, getSeriesSeasons } from '../services/series.js'
import { createRequestGuard } from '../features/requestGuard.js'
import VideoPlayer from '../components/VideoPlayer.jsx'
import FavoriteButton from '../components/FavoriteButton.jsx'
import ReviewSection from '../components/ReviewSection.jsx'
import SeoHead from '../components/SeoHead.jsx'

export default function SeriesEpisodePage() {
  const { slug, episodeSlug } = useParams()
  const [episode, setEpisode] = useState(null)
  const [series, setSeries] = useState(null)
  const [seasonTitle, setSeasonTitle] = useState('')
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
    setSeasonTitle('')
    Promise.all([
      getSeriesEpisode(slug, episodeSlug, { signal: controller.signal }),
      getSeriesDetail(slug, { signal: controller.signal }),
      getSeriesSeasons(slug, { signal: controller.signal }),
    ]).then(([episodeResponse, seriesResponse, seasonsResponse]) => {
      if (!request.current.isCurrent(token)) return
      setEpisode(episodeResponse.data)
      setSeries(seriesResponse.data)
      const season = seasonsResponse.data.find((item) => item.id === episodeResponse.data.season_id)
      setSeasonTitle(season?.title || (season ? `Season ${season.season_number}` : ''))
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

  if (loading) return <><SeoHead title="Episode | CineSplit" noIndex/><p role="status" className="movie-state">Loading episode…</p></>
  if (error || !episode || !series) return <><SeoHead title="Episode not found | CineSplit" noIndex/><section><p role="alert" className="movie-state">{error || 'Episode not found.'}</p><Link className="quiet-button" to={`/series/${encodeURIComponent(slug)}`}><FontAwesomeIcon icon={faArrowLeft}/> Back to series</Link></section></>
  const seoDescription = episode.description || `${episode.title} from ${series.title}.`
  const episodeLabel = episode.type === 'special'
    ? `Special ${episode.special_number}: ${episode.title}`
    : `${seasonTitle ? `${seasonTitle}, ` : ''}Episode ${episode.episode_number}: ${episode.title}`
  const episodeSchema = {
    '@context': 'https://schema.org',
    '@type': 'TVEpisode',
    name: episode.title,
    description: seoDescription,
    ...(episode.poster_media?.secure_url ? { image: episode.poster_media.secure_url } : {}),
    ...(episode.type === 'regular' && episode.episode_number ? { episodeNumber: episode.episode_number } : {}),
    ...(episode.release_date ? { datePublished: episode.release_date } : {}),
    ...(episode.duration ? { duration: `PT${episode.duration}M` } : {}),
    partOfSeries: { '@type': 'TVSeries', name: series.title, url: `${(import.meta.env.VITE_PUBLIC_SITE_URL || '').replace(/\/+$/, '')}/series/${series.slug}/` },
  }
  const siteUrl = (import.meta.env.VITE_PUBLIC_SITE_URL || '').replace(/\/+$/, '')
  const breadcrumbSchema = siteUrl ? {
    '@context': 'https://schema.org', '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Series', item: `${siteUrl}/series/` },
      { '@type': 'ListItem', position: 2, name: series.title, item: `${siteUrl}/series/${series.slug}/` },
      { '@type': 'ListItem', position: 3, name: episode.title, item: `${siteUrl}/series/${series.slug}/episodes/${episode.slug}/` },
    ],
  } : null
  if (!siteUrl) delete episodeSchema.partOfSeries.url
  return <article className="episode-detail"><SeoHead title={`${episodeLabel} | ${series.title} | CineSplit`} description={seoDescription} path={`/series/${series.slug}/episodes/${episode.slug}/`} image={episode.poster_media?.secure_url || series.poster_url} schema={[episodeSchema, breadcrumbSchema]} noIndex={String(episode.description || '').trim().length < 40}/><Link className="quiet-button" to={`/series/${encodeURIComponent(slug)}`}><FontAwesomeIcon icon={faArrowLeft}/> Back to {series.title}</Link><div className="episode-detail-art"><span className="eyebrow">{episode.type === 'special' ? `SPECIAL ${episode.special_number}` : `SEASON EPISODE ${episode.episode_number}`}</span><h1>{episode.title}</h1><p><FontAwesomeIcon icon={faClock}/> {episode.duration} min {episode.release_date && ` · ${episode.release_date}`}</p><p>{episode.description || 'More details for this episode will be available soon.'}</p></div><FavoriteButton contentType="episode" contentId={episode.id}/><VideoPlayer video={episode.video} poster={episode.poster_media} title={episode.title} contentType="episode" contentId={episode.id}/><ReviewSection contentType="episode" contentId={episode.id}/></article>
}
