import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faImage, faUpload, faVideo } from '@fortawesome/free-solid-svg-icons'
import { getAdminMedia, uploadAdminMedia } from '../services/media.js'

export default function MediaUploader({ contentType, contentId }) {
  const [media, setMedia] = useState({ video: null, poster: null })
  const [progress, setProgress] = useState({ video: null, poster: null })
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let current = true
    getAdminMedia(contentType, contentId).then(({ data }) => { if (current) setMedia(data) }).catch((requestError) => {
      if (current) setError(requestError.response?.data?.detail || 'Current media could not be loaded.')
    })
    return () => { current = false }
  }, [contentType, contentId])

  async function upload(role, file) {
    if (!file) return
    setBusy(role); setError(''); setNotice(''); setProgress((items) => ({ ...items, [role]: 0 }))
    try {
      const { data } = await uploadAdminMedia(contentType, contentId, role, file, (event) => {
        if (event.total) setProgress((items) => ({ ...items, [role]: Math.round(event.loaded * 100 / event.total) }))
      })
      setMedia((items) => ({ ...items, [role]: data }))
      setNotice(`${role === 'video' ? 'Video' : 'Poster'} uploaded and associated.`)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Upload failed. Check the file and try again.')
    } finally { setBusy(''); setProgress((items) => ({ ...items, [role]: null })) }
  }

  return <section className="media-uploader" aria-label="Content media">
    <h4>Media</h4>
    {error && <p className="form-alert" role="alert">{error}</p>}{notice && <p className="form-notice" role="status">{notice}</p>}
    <div className="media-upload-controls">
      <label><FontAwesomeIcon icon={faVideo} /> {media.video ? 'Replace video' : 'Upload video'}<input type="file" accept="video/mp4,video/webm,video/quicktime,video/x-m4v" disabled={Boolean(busy)} onChange={(event) => { void upload('video', event.target.files?.[0]); event.target.value = '' }} /></label>
      <label><FontAwesomeIcon icon={faImage} /> {media.poster ? 'Replace poster' : 'Upload poster'}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={Boolean(busy)} onChange={(event) => { void upload('poster', event.target.files?.[0]); event.target.value = '' }} /></label>
    </div>
    {busy && <p role="status"><FontAwesomeIcon icon={faUpload} /> Uploading {busy}… {progress[busy] ?? 0}%</p>}
    <div className="media-current">{media.video && <a href={media.video.secure_url} target="_blank" rel="noreferrer">Current video · {media.video.format || 'video'}{media.video.duration ? ` · ${Math.round(media.video.duration)} sec` : ''}</a>}{media.poster && <a href={media.poster.secure_url} target="_blank" rel="noreferrer">Current poster · {media.poster.format || 'image'}</a>}{!media.video && !media.poster && <span>No media uploaded yet.</span>}</div>
  </section>
}
