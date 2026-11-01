import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faClock } from '@fortawesome/free-solid-svg-icons'
import { getSeriesDetail, getSeriesSeasons, getSeasonEpisodes, getSeriesSpecials } from '../services/series.js'
import { createRequestGuard } from '../features/requestGuard.js'
import FavoriteButton from '../components/FavoriteButton.jsx'
import ReviewSection from '../components/ReviewSection.jsx'

export default function SeriesDetailPage() {
  const { slug } = useParams()
  const [series, setSeries] = useState(null)
  const [seasons, setSeasons] = useState([])
  const [season, setSeason] = useState('')
  const [episodes, setEpisodes] = useState([])
  const [specials, setSpecials] = useState([])
  const [error, setError] = useState('')
  const [episodeError, setEpisodeError] = useState('')
  const [loading, setLoading] = useState(true)
  const [episodesLoading, setEpisodesLoading] = useState(false)
  const seriesRequest = useRef(null)
  const episodeRequest = useRef(null)
  if (!seriesRequest.current) seriesRequest.current = createRequestGuard()
  if (!episodeRequest.current) episodeRequest.current = createRequestGuard()

  useEffect(() => {
    const token = seriesRequest.current.begin()
    const controller = new AbortController()
    setError('')
    setEpisodeError('')
    setLoading(true)
    setSeries(null)
    setSeasons([])
    setSeason('')
    setEpisodes([])
    setSpecials([])
    Promise.all([
      getSeriesDetail(slug, { signal: controller.signal }),
      getSeriesSeasons(slug, { signal: controller.signal }),
      getSeriesSpecials(slug, { signal: controller.signal }),
    ]).then(([seriesResponse, seasonsResponse, specialsResponse]) => {
      if (!seriesRequest.current.isCurrent(token)) return
      setSeries(seriesResponse.data)
      setSeasons(seasonsResponse.data)
      setSpecials(specialsResponse.data)
      setSeason(seasonsResponse.data[0]?.slug || '')
      setError('')
    }).catch((requestError) => {
      if (seriesRequest.current.isCurrent(token) && requestError.name !== 'CanceledError') {
        setError(requestError.response?.data?.detail || 'Series could not be loaded.')
      }
    }).finally(() => {
      if (seriesRequest.current.isCurrent(token)) setLoading(false)
    })
    return () => { controller.abort(); seriesRequest.current.invalidate() }
  }, [slug])

  useEffect(() => {
    const token = episodeRequest.current.begin()
    if (!season) {
      setEpisodes([])
      setEpisodesLoading(false)
      setEpisodeError('')
      return () => episodeRequest.current.invalidate()
    }
    const controller = new AbortController()
    setEpisodes([])
    setEpisodesLoading(true)
    setEpisodeError('')
    getSeasonEpisodes(slug, season, { signal: controller.signal }).then(({ data }) => {
      if (!episodeRequest.current.isCurrent(token)) return
      setEpisodes(data)
      setEpisodeError('')
    }).catch((requestError) => {
      if (episodeRequest.current.isCurrent(token) && requestError.name !== 'CanceledError') {
        setEpisodeError(requestError.response?.data?.detail || 'Episodes could not be loaded.')
      }
    }).finally(() => {
      if (episodeRequest.current.isCurrent(token)) setEpisodesLoading(false)
    })
    return () => { controller.abort(); episodeRequest.current.invalidate() }
  }, [slug, season])

  if (loading) return <p className="movie-state" role="status">Loading series…</p>
  if (error || !series) return <section className="series-error"><p className="movie-state" role="alert">{error || 'Series not found.'}</p><Link className="quiet-button" to="/series"><FontAwesomeIcon icon={faArrowLeft}/> All series</Link></section>

  return (
    <article className="series-detail">
      <Link className="quiet-button" to="/series"><FontAwesomeIcon icon={faArrowLeft}/> All series</Link>
      <section className="series-detail-hero" style={series.backdrop_url ? { backgroundImage: `linear-gradient(90deg,#101011 0%,#101011dd 48%,#10101155),url("${series.backdrop_url}")` } : {}}>
        <div className="series-detail-poster">{series.poster_url ? <img src={series.poster_url} alt={`${series.title} poster`}/> : <span>{series.title}</span>}</div>
        <div className="series-detail-copy"><span className="eyebrow">{series.release_year} · {series.content_rating} · {series.language}</span><h1>{series.title}</h1><p className="series-genres">{series.genres?.join(' · ')}</p><p>{series.description || series.short_description}</p><dl className="series-facts"><div><dt>Director</dt><dd>{series.director || '—'}</dd></div><div><dt>Cast</dt><dd>{series.cast?.join(', ') || '—'}</dd></div><div><dt>Production</dt><dd>{series.production_company || '—'}</dd></div></dl></div>
      </section>
      <FavoriteButton contentType="series" contentId={series.id}/>
      <section className="series-episodes-section"><div className="series-section-heading"><div><span className="eyebrow">THE STORY CONTINUES</span><h2>Episodes</h2></div><label className="season-select">Season<select aria-label="Choose a season" value={season} onChange={(event) => setSeason(event.target.value)}>{seasons.map((item) => <option key={item.id} value={item.slug}>{item.title || `Season ${item.season_number}`}</option>)}</select></label></div>
        {!season ? <p className="movie-state">No published seasons yet.</p> : episodesLoading ? <p className="movie-state" role="status">Loading episodes…</p> : episodeError ? <p className="movie-state" role="alert">{episodeError}</p> : episodes.length ? <div className="episode-list">{episodes.map((episode) => <Link className="episode-row" to={`/series/${encodeURIComponent(slug)}/episodes/${encodeURIComponent(episode.slug)}`} key={episode.id}><span className="episode-number">{String(episode.episode_number).padStart(2, '0')}</span><span className="episode-copy"><strong>{episode.title}</strong><span>{episode.description}</span></span><span className="episode-duration"><FontAwesomeIcon icon={faClock}/> {episode.duration} min</span></Link>)}</div> : <p className="movie-state">No published episodes in this season yet.</p>}
      </section>
      {specials.length > 0 && <section className="series-episodes-section"><div className="series-section-heading"><div><span className="eyebrow">BEYOND THE SEASONS</span><h2>Specials</h2></div></div><div className="episode-list">{specials.map((episode) => <Link className="episode-row" to={`/series/${encodeURIComponent(slug)}/episodes/${encodeURIComponent(episode.slug)}`} key={episode.id}><span className="episode-number">S{String(episode.special_number).padStart(2, '0')}</span><span className="episode-copy"><strong>{episode.title}</strong><span>{episode.description}</span></span><span className="episode-duration"><FontAwesomeIcon icon={faClock}/> {episode.duration} min</span></Link>)}</div></section>}
      <ReviewSection contentType="series" contentId={series.id}/>
    </article>
  )
}
