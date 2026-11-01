import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { after, before, test } from 'node:test'
import { createServer } from 'vite'

const source = (path) => readFile(new URL(path, import.meta.url), 'utf8')
let vite
let api
let movieApi
let chapterApi

before(async () => {
  vite = await createServer({ configFile: 'vite.config.js', server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  api = (await vite.ssrLoadModule('/src/services/api.js')).default
  movieApi = await vite.ssrLoadModule('/src/services/movies.js')
  chapterApi = await vite.ssrLoadModule('/src/services/chapters.js')
})

after(async () => {
  if (vite) await vite.close()
})

test('movie service requests resolve to the backend and preserve API paths and credentials', async () => {
  const requests = []
  api.defaults.adapter = async (config) => {
    requests.push({ method: config.method.toUpperCase(), url: api.getUri(config), withCredentials: config.withCredentials })
    return { data: [], status: 200, statusText: 'OK', headers: {}, config }
  }

  await movieApi.getMovies({ search: 'moon', genre: 'drama', page: 2 })
  await movieApi.getFeaturedMovies()
  await movieApi.getMovieGenres()
  await movieApi.getMovie('moon-river')
  await movieApi.getAdminMovies()
  await movieApi.createAdminMovie({ title: 'Moon River' })
  await movieApi.updateAdminMovie('65f000000000000000000001', { is_featured: true })
  await movieApi.deleteAdminMovie('65f000000000000000000001', 'moon-river')

  assert.deepEqual(requests.map(({ method, url }) => [method, url.split('?')[0]]), [
    ['GET', 'http://localhost:8000/api/movies/'],
    ['GET', 'http://localhost:8000/api/movies/featured/'],
    ['GET', 'http://localhost:8000/api/movies/genres/'],
    ['GET', 'http://localhost:8000/api/movies/moon-river/'],
    ['GET', 'http://localhost:8000/api/admin/movies/'],
    ['POST', 'http://localhost:8000/api/admin/movies/'],
    ['PATCH', 'http://localhost:8000/api/admin/movies/65f000000000000000000001/'],
    ['DELETE', 'http://localhost:8000/api/admin/movies/65f000000000000000000001/'],
  ])
  assert.equal(requests.every((request) => request.withCredentials), true)
  assert.equal(requests.some((request) => request.url.includes(':5174') || request.url.includes(':5000')), false)
  assert.match(requests[0].url, /search=moon/)
  assert.match(requests[0].url, /genre=drama/)
})

test('catalog includes title search, movie filters, sort controls, pagination, and results states', async () => {
  const [catalog, grid] = await Promise.all([source('../src/pages/MovieCatalogPage.jsx'), source('../src/components/MovieGrid.jsx')])
  assert.match(catalog, /type="search"/)
  assert.match(catalog, /release_year/)
  assert.match(catalog, /content_rating/)
  assert.match(catalog, /value="-release_year"/)
  assert.match(catalog, /movie-pagination/)
  assert.match(catalog, /<MovieGrid/)
  assert.match(grid, /role="status"/)
  assert.match(grid, /role="alert"/)
  assert.match(grid, /No movies match those filters/)
})

test('movie card links by slug and presents title, year, genres, duration, and rating', async () => {
  const card = await source('../src/components/MovieCard.jsx')
  assert.match(card, /to=\{`\/movies\/\$\{encodeURIComponent\(movie\.slug\)\}`\}/)
  for (const field of ['movie.title', 'movie.release_year', 'movie.genres', 'movie.duration_minutes', 'movie.content_rating']) {
    assert.ok(card.includes(field), `Movie card should render ${field}`)
  }
})

test('movie detail displays requested metadata and handles loading and errors', async () => {
  const detail = await source('../src/pages/MovieDetailPage.jsx')
  for (const field of ['movie.title', 'movie.description', 'movie.release_year', 'movie.genres', 'movie.duration_minutes', 'movie.original_language', 'movie.cast', 'movie.director', 'movie.content_rating']) {
    assert.ok(detail.includes(field), `Movie detail should render ${field}`)
  }
  assert.match(detail, /Loading film/)
  assert.match(detail, /role="alert"/)
})

test('admin form validates required movie data and admin route requires backend role', async () => {
  const [editor, adminPage, protectedRoute] = await Promise.all([
    source('../src/components/MovieEditor.jsx'),
    source('../src/pages/AdminMoviesPage.jsx'),
    source('../src/components/ProtectedRoute.jsx'),
  ])
  assert.match(editor, /name="title"[^>]*required/)
  assert.match(editor, /name="release_year"[^>]*required/)
  assert.match(editor, /name="duration_minutes"[^>]*required/)
  assert.match(editor, /name="genres"[^>]*required/)
  assert.match(editor, /name="status"/)
  assert.match(editor, /name="is_featured"/)
  assert.match(editor, /production_company: movie\.production_company/)
  assert.doesNotMatch(editor, /return \{ \.\.\.movie/)
  assert.match(adminPage, /updateAdminMovie/)
  assert.match(adminPage, /deleteAdminMovie/)
  assert.match(adminPage, /window\.confirm/)
  assert.match(protectedRoute, /user\.role !== requiredRole/)
})

test('application route components are imported so React can render the route tree', async () => {
  const app = await source('../src/App.jsx')
  assert.match(app, /import StatusPage from '\.\/pages\/StatusPage\.jsx'/)
  assert.match(app, /element=\{<StatusPage \/>\}/)
  assert.match(app, /element=\{<MovieCatalogPage \/>\}/)
})

test('chapter services use the shared backend client for public and admin endpoints', async () => {
  const requests = []
  api.defaults.adapter = async (config) => {
    requests.push({ method: config.method.toUpperCase(), url: api.getUri(config), withCredentials: config.withCredentials, data: config.data })
    return { data: [], status: 200, statusText: 'OK', headers: {}, config }
  }
  await chapterApi.getPublicChapters('moon-river')
  await chapterApi.getAdminChapters('65f000000000000000000001')
  await chapterApi.createAdminChapter('65f000000000000000000001', { title: 'Arrival' })
  await chapterApi.updateAdminChapter('65f000000000000000000001', '65f000000000000000000002', { status: 'published' })
  await chapterApi.deleteAdminChapter('65f000000000000000000001', '65f000000000000000000002')
  await chapterApi.reorderAdminChapters('65f000000000000000000001', ['65f000000000000000000002'])
  assert.deepEqual(requests.map(({ method, url }) => [method, url.split('?')[0]]), [
    ['GET', 'http://localhost:8000/api/movies/moon-river/chapters/'],
    ['GET', 'http://localhost:8000/api/admin/movies/65f000000000000000000001/chapters/'],
    ['POST', 'http://localhost:8000/api/admin/movies/65f000000000000000000001/chapters/'],
    ['PATCH', 'http://localhost:8000/api/admin/movies/65f000000000000000000001/chapters/65f000000000000000000002/'],
    ['DELETE', 'http://localhost:8000/api/admin/movies/65f000000000000000000001/chapters/65f000000000000000000002/'],
    ['POST', 'http://localhost:8000/api/admin/movies/65f000000000000000000001/chapters/reorder/'],
  ])
  assert.equal(requests.every((request) => request.withCredentials), true)
  assert.match(requests.at(-1).data, /chapter_ids/)
})

test('chapter admin and public screens cover management, publication, order, empty and error states', async () => {
  const [admin, detail] = await Promise.all([
    source('../src/components/ChapterManagement.jsx'),
    source('../src/pages/MovieDetailPage.jsx'),
  ])
  for (const expectation of [/Add a chapter/, /Edit chapter/, /Save order/, /Publish/, /Delete/, /No chapters yet/, /role="alert"/, /reorderAdminChapters/]) {
    assert.match(admin, expectation)
  }
  for (const expectation of [/chapter\.chapter_number/, /chapter\.title/, /chapter\.description/, /chapter\.duration/, /chapter\.is_free/, /No published chapters/]) {
    assert.match(detail, expectation)
  }
})
