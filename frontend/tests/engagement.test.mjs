import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createServer } from 'vite'

let vite
let api
let engagement

before(async () => {
  vite = await createServer({ configFile: 'vite.config.js', server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  api = (await vite.ssrLoadModule('/src/services/api.js')).default
  engagement = await vite.ssrLoadModule('/src/services/engagement.js')
})

after(async () => { if (vite) await vite.close() })

test('favorites, watch progress, reviews and discovery use the shared credentialed API client', async () => {
  const requests = []
  api.defaults.adapter = async (config) => {
    requests.push({ method: config.method.toUpperCase(), url: api.getUri(config), body: config.data, credentials: config.withCredentials })
    return { data: { results: [] }, status: 200, statusText: 'OK', headers: {}, config }
  }
  await engagement.addFavorite('movie', '65f000000000000000000001')
  await engagement.getFavorites({ page: 2 })
  await engagement.removeFavorite('movie', '65f000000000000000000001')
  await engagement.saveWatchProgress({ content_type: 'episode', content_id: '65f000000000000000000002', position: 30 })
  await engagement.getWatchHistory({ continue_watching: true })
  await engagement.getReviews('series', '65f000000000000000000003')
  await engagement.createReview('series', '65f000000000000000000003', { rating: 5, body: 'Loved it' })
  await engagement.getDiscovery({ search: 'north', page: 2 })
  await engagement.getDashboard()
  assert.equal(requests.length, 9)
  assert.ok(requests.every((request) => request.credentials))
  assert.match(requests[0].url, /\/favorites\/$/)
  assert.match(requests[2].url, /\/favorites\/movie\/65f000000000000000000001\/$/)
  assert.match(requests[3].url, /\/watch-history\/$/)
  assert.match(requests[6].url, /\/reviews\/series\/65f000000000000000000003\/$/)
  assert.match(requests[7].url, /\/discover\//)
  assert.match(requests[8].url, /\/admin\/analytics\//)
})
