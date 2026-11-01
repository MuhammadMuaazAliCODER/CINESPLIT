import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faClock, faStar } from '@fortawesome/free-solid-svg-icons'
import { Link } from 'react-router-dom'
import FavoriteButton from './FavoriteButton.jsx'

export default function MovieCard({ movie }) {
  return (
    <article className="movie-card movie-card-with-favorite">
      <Link className="movie-card-link" to={`/movies/${encodeURIComponent(movie.slug)}`} aria-label={`View ${movie.title}`}>
        <div className="movie-poster">
          {movie.poster_url ? <img src={movie.poster_url} alt={`${movie.title} poster`} loading="lazy" /> : <div className="poster-placeholder" aria-hidden="true"><span>{movie.title}</span></div>}
          {movie.is_featured && <span className="featured-badge"><FontAwesomeIcon icon={faStar} aria-hidden="true" /> Featured</span>}
          <span className="rating-badge">{movie.content_rating}</span>
        </div>
        <div className="movie-card-copy">
          <div className="movie-card-heading"><h2>{movie.title}</h2><span>{movie.release_year}</span></div>
          <p>{movie.short_description}</p>
          <div className="movie-card-meta">
            <span>{movie.genres.map((genre) => genre.replace(/\b\w/g, (letter) => letter.toUpperCase())).join(' · ')}</span>
            <span><FontAwesomeIcon icon={faClock} aria-hidden="true" /> {movie.duration_minutes} min</span>
          </div>
        </div>
      </Link>
      <FavoriteButton contentType="movie" contentId={movie.id} compact/>
    </article>
  )
}
