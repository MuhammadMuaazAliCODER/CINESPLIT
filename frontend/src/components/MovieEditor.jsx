import { useEffect, useState } from 'react'

const emptyMovie = {
  title: '', slug: '', short_description: '', description: '', release_year: new Date().getFullYear(),
  genres: '', original_language: '', duration_minutes: '', content_rating: 'PG-13', cast: '', director: '',
  production_company: '', country: '', status: 'draft', is_featured: false, poster_url: '', backdrop_url: '',
}

function toForm(movie) {
  if (!movie) return { ...emptyMovie }
  return {
    title: movie.title,
    slug: movie.slug,
    short_description: movie.short_description,
    description: movie.description,
    release_year: movie.release_year,
    genres: movie.genres.join(', '),
    original_language: movie.original_language,
    duration_minutes: movie.duration_minutes,
    content_rating: movie.content_rating,
    cast: movie.cast.join(', '),
    director: movie.director,
    production_company: movie.production_company,
    country: movie.country,
    status: movie.status,
    is_featured: movie.is_featured,
    poster_url: movie.poster_url || '',
    backdrop_url: movie.backdrop_url || '',
  }
}

export default function MovieEditor({ movie, saving = false, onSubmit, onCancel, error = '' }) {
  const [form, setForm] = useState(() => toForm(movie))
  useEffect(() => setForm(toForm(movie)), [movie])

  function change(event) {
    const { name, value, type, checked } = event.target
    setForm((current) => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
  }

  function submit(event) {
    event.preventDefault()
    const data = {
      ...form,
      release_year: Number(form.release_year),
      duration_minutes: Number(form.duration_minutes),
      genres: form.genres.split(',').map((part) => part.trim()).filter(Boolean),
      cast: form.cast.split(',').map((part) => part.trim()).filter(Boolean),
    }
    void onSubmit(data)
  }

  return (
    <form className="movie-editor" onSubmit={submit}>
      <div className="movie-editor-heading"><div><span className="eyebrow">{movie ? 'EDIT THE FILM' : 'ADD TO THE COLLECTION'}</span><h2>{movie ? movie.title : 'Create a movie'}</h2></div>{movie && <button className="quiet-button" type="button" onClick={onCancel}>Cancel</button>}</div>
      <div className="movie-editor-grid">
        <label>Title<input name="title" value={form.title} onChange={change} maxLength={180} required /></label>
        <label>Slug <span className="field-hint">Leave blank to generate from title</span><input name="slug" value={form.slug || ''} onChange={change} maxLength={200} /></label>
        <label>Release year<input name="release_year" type="number" min="1870" max="2100" value={form.release_year} onChange={change} required /></label>
        <label>Duration (minutes)<input name="duration_minutes" type="number" min="1" max="1000" value={form.duration_minutes} onChange={change} required /></label>
        <label>Genres <span className="field-hint">Comma separated</span><input name="genres" value={form.genres} onChange={change} placeholder="drama, mystery" required /></label>
        <label>Original language<input name="original_language" value={form.original_language} onChange={change} maxLength={50} required /></label>
        <label>Content rating<select name="content_rating" value={form.content_rating} onChange={change}>{['G', 'PG', 'PG-13', 'R', 'NC-17', 'TV-G', 'TV-PG', 'TV-14', 'TV-MA', 'NR'].map((rating) => <option key={rating}>{rating}</option>)}</select></label>
        <label>Director<input name="director" value={form.director} onChange={change} maxLength={120} required /></label>
        <label>Production company<input name="production_company" value={form.production_company} onChange={change} maxLength={160} required /></label>
        <label>Country<input name="country" value={form.country} onChange={change} maxLength={100} required /></label>
        <label>Cast <span className="field-hint">Comma separated</span><input name="cast" value={form.cast} onChange={change} maxLength={4000} /></label>
        <label>Publication<select name="status" value={form.status} onChange={change}><option value="draft">Draft</option><option value="published">Published</option></select></label>
        <label className="movie-editor-wide">Short description<textarea name="short_description" value={form.short_description} onChange={change} maxLength={280} rows="2" required /></label>
        <label className="movie-editor-wide">Full description<textarea name="description" value={form.description} onChange={change} maxLength={12000} rows="5" required /></label>
        <label>Poster URL placeholder<input name="poster_url" type="url" value={form.poster_url || ''} onChange={change} maxLength={2048} /></label>
        <label>Backdrop URL placeholder<input name="backdrop_url" type="url" value={form.backdrop_url || ''} onChange={change} maxLength={2048} /></label>
        <label className="movie-featured-toggle"><input name="is_featured" type="checkbox" checked={Boolean(form.is_featured)} onChange={change} /> Feature this film</label>
      </div>
      {error && <p className="form-alert" role="alert">{error}</p>}
      <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Saving film…' : movie ? 'Save changes' : 'Create movie'}</button>
    </form>
  )
}
