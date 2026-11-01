import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createServer } from 'vite'

let vite
let api
let seriesApi
let pagination
let requestGuard

before(async () => {
  vite = await createServer({ configFile: 'vite.config.js', server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  api = (await vite.ssrLoadModule('/src/services/api.js')).default
  seriesApi = await vite.ssrLoadModule('/src/services/series.js')
  pagination = await vite.ssrLoadModule('/src/features/pagination.js')
  requestGuard = await vite.ssrLoadModule('/src/features/requestGuard.js')
})

after(async () => { if (vite) await vite.close() })

test('series services call public and administrator routes with paging and parent identifiers', async () => {
  const requests = []
  api.defaults.adapter = async (config) => {
    requests.push({ method: config.method.toUpperCase(), url: api.getUri(config), data: config.data, withCredentials: config.withCredentials })
    return { data: { results: [], page: 2, page_size: 20, pages: 4, total: 61 }, status: 200, statusText: 'OK', headers: {}, config }
  }
  const id = '65f000000000000000000001'
  const seasonId = '65f000000000000000000002'
  const episodeId = '65f000000000000000000003'
  await seriesApi.getSeries({ page: 2, page_size: 20, genre: 'drama' })
  await seriesApi.getFeaturedSeries()
  await seriesApi.getSeriesGenres()
  await seriesApi.getSeriesDetail('north-road')
  await seriesApi.getSeriesSeasons('north-road')
  await seriesApi.getSeasonEpisodes('north-road', 'season-one')
  await seriesApi.getSeriesSpecials('north-road')
  await seriesApi.getSeriesEpisode('north-road', 'pilot')
  await seriesApi.getAdminSeries({ page: 2, page_size: 20 })
  await seriesApi.createAdminSeries({ title: 'North Road' })
  await seriesApi.updateAdminSeries(id, { status: 'published' })
  await seriesApi.deleteAdminSeries(id, 'north-road')
  await seriesApi.getAdminSeasons(id)
  await seriesApi.createAdminSeason(id, { title: 'Season One' })
  await seriesApi.updateAdminSeason(id, seasonId, { title: 'Season One' })
  await seriesApi.deleteAdminSeason(id, seasonId)
  await seriesApi.reorderAdminSeasons(id, [seasonId])
  await seriesApi.getAdminEpisodes(id, seasonId)
  await seriesApi.createAdminEpisode(id, { title: 'Pilot' }, seasonId)
  await seriesApi.reorderAdminEpisodes(id, [episodeId], seasonId)
  await seriesApi.getAdminEpisodes(id)
  await seriesApi.createAdminEpisode(id, { title: 'Reunion' })
  await seriesApi.reorderAdminEpisodes(id, [episodeId])
  await seriesApi.updateAdminEpisode(id, episodeId, { title: 'Pilot' })
  await seriesApi.deleteAdminEpisode(id, episodeId)

  assert.deepEqual(requests.map(({ method, url }) => [method, url.split('?')[0]]), [
    ['GET','http://localhost:8000/api/series/'],['GET','http://localhost:8000/api/series/featured/'],['GET','http://localhost:8000/api/series/genres/'],
    ['GET','http://localhost:8000/api/series/north-road/'],['GET','http://localhost:8000/api/series/north-road/seasons/'],
    ['GET','http://localhost:8000/api/series/north-road/seasons/season-one/episodes/'],['GET','http://localhost:8000/api/series/north-road/specials/'],
    ['GET','http://localhost:8000/api/series/north-road/episodes/pilot/'],['GET','http://localhost:8000/api/admin/series/'],['POST','http://localhost:8000/api/admin/series/'],
    ['PATCH',`http://localhost:8000/api/admin/series/${id}/`],['DELETE',`http://localhost:8000/api/admin/series/${id}/`],
    ['GET',`http://localhost:8000/api/admin/series/${id}/seasons/`],['POST',`http://localhost:8000/api/admin/series/${id}/seasons/`],
    ['PATCH',`http://localhost:8000/api/admin/series/${id}/seasons/${seasonId}/`],['DELETE',`http://localhost:8000/api/admin/series/${id}/seasons/${seasonId}/`],
    ['POST',`http://localhost:8000/api/admin/series/${id}/seasons/reorder/`],['GET',`http://localhost:8000/api/admin/series/${id}/seasons/${seasonId}/episodes/`],
    ['POST',`http://localhost:8000/api/admin/series/${id}/seasons/${seasonId}/episodes/`],['POST',`http://localhost:8000/api/admin/series/${id}/seasons/${seasonId}/episodes/reorder/`],
    ['GET',`http://localhost:8000/api/admin/series/${id}/specials/`],['POST',`http://localhost:8000/api/admin/series/${id}/specials/`],
    ['POST',`http://localhost:8000/api/admin/series/${id}/specials/reorder/`],['PATCH',`http://localhost:8000/api/admin/series/${id}/episodes/${episodeId}/`],
    ['DELETE',`http://localhost:8000/api/admin/series/${id}/episodes/${episodeId}/`],
  ])
  assert.equal(requests.every((request) => request.withCredentials), true)
  assert.match(requests[0].url, /page=2/)
  assert.match(requests[0].url, /page_size=20/)
  assert.match(requests[11].data, /confirmation/)
})

test('catalogue and studio page transitions clamp at their valid page boundaries', () => {
  assert.equal(pagination.previousPage(1, 4), 1)
  assert.equal(pagination.nextPage(4, 4), 4)
  assert.equal(pagination.nextPage(2, 4), 3)
  assert.equal(pagination.clampPage(3, 0), 1)
  assert.equal(pagination.clampPage(9, 4), 4)
})

test('a newer route request invalidates an older in-flight response', () => {
  const guard = requestGuard.createRequestGuard()
  const oldRequest = guard.begin()
  const newRequest = guard.begin()
  assert.equal(guard.isCurrent(oldRequest), false)
  assert.equal(guard.isCurrent(newRequest), true)
  guard.invalidate()
  assert.equal(guard.isCurrent(newRequest), false)
})
