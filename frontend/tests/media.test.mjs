import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createServer } from 'vite'

let vite
let api
let mediaApi

before(async () => {
  vite = await createServer({ configFile: 'vite.config.js', server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  api = (await vite.ssrLoadModule('/src/services/api.js')).default
  mediaApi = await vite.ssrLoadModule('/src/services/media.js')
})

after(async () => { if (vite) await vite.close() })

test('admin media upload posts multipart content and surfaces upload progress', async () => {
  let request
  const progress = () => {}
  api.defaults.adapter = async (config) => {
    request = config
    return { data: { public_id: 'asset1' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  await mediaApi.uploadAdminMedia('episode', '65f000000000000000000001', 'video', new Blob(['video'], { type: 'video/mp4' }), progress)
  assert.equal(request.method, 'post')
  assert.match(api.getUri(request), /\/admin\/media\/episode\/65f000000000000000000001\/video\/$/)
  assert.equal(request.data.get('file').type, 'video/mp4')
  assert.equal(request.onUploadProgress, progress)
  assert.equal(request.withCredentials, true)
})

test('admin media association lookup uses the content type and id route', async () => {
  let request
  api.defaults.adapter = async (config) => {
    request = config
    return { data: { video: null, poster: null }, status: 200, statusText: 'OK', headers: {}, config }
  }
  await mediaApi.getAdminMedia('movie', '65f000000000000000000002')
  assert.equal(request.method, 'get')
  assert.match(api.getUri(request), /\/admin\/media\/movie\/65f000000000000000000002\/$/)
})
