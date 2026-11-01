import MovieCard from './MovieCard.jsx'

export default function MovieGrid({ movies = [], loading = false, error = '', emptyMessage = 'No movies match those filters.' }) {
  if (loading) return <p className="movie-state" role="status">Finding your next story…</p>
  if (error) return <p className="movie-state movie-state-error" role="alert">{error}</p>
  if (!movies.length) return <p className="movie-state" role="status">{emptyMessage}</p>
  return <div className="movie-grid">{movies.map((movie, index) => <MovieCard key={movie.id} movie={movie} priority={index < 4} />)}</div>
}
