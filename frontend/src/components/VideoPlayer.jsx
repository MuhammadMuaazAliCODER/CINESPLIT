import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faCompress,
  faExpand,
  faGear,
  faPause,
  faPlay,
  faRotateLeft,
  faRotateRight,
  faVolumeHigh,
  faVolumeLow,
  faVolumeXmark,
} from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../context/AuthContext.jsx'
import { getWatchProgress, saveWatchProgress } from '../services/engagement.js'

const QUALITY_LEVELS = [
  { label: '1080p', width: 1920 },
  { label: '720p', width: 1280 },
  { label: '480p', width: 854 },
  { label: '360p', width: 640 },
]
const PLAYBACK_RATES = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  const total = Math.floor(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const remainder = total % 60
  return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
    : `${minutes}:${String(remainder).padStart(2, '0')}`
}

function getQualitySource(url, quality) {
  if (quality === 'Auto') return url
  const level = QUALITY_LEVELS.find((item) => item.label === quality)
  if (!level || !url?.includes('/video/upload/')) return url
  return url.replace('/video/upload/', `/video/upload/c_limit,w_${level.width},q_auto/`)
}

export default function VideoPlayer({ video, poster, title, contentType, contentId }) {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [progressError, setProgressError] = useState('')
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [muted, setMuted] = useState(false)
  const [quality, setQuality] = useState('Auto')
  const [playbackRate, setPlaybackRate] = useState(1)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsPage, setSettingsPage] = useState('main')
  const [fullscreen, setFullscreen] = useState(false)
  const videoRef = useRef(null)
  const stageRef = useRef(null)
  const lastSavedAt = useRef(0)
  const saving = useRef(false)
  const queued = useRef(null)
  const requestGeneration = useRef(0)
  const pendingSourceRestore = useRef(null)
  const savedPosition = useRef(null)
  const source = useMemo(() => getQualitySource(video?.secure_url, quality), [video?.secure_url, quality])
  const hasQualityOptions = Boolean(video?.secure_url?.includes('/video/upload/'))
  const seekPercent = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0

  useEffect(() => {
    const generation = ++requestGeneration.current
    savedPosition.current = null
    lastSavedAt.current = 0
    if (!user || !contentId) return () => { requestGeneration.current += 1 }
    getWatchProgress(contentType, contentId).then(({ data }) => {
      if (generation !== requestGeneration.current || data.completed || !(data.position > 0)) return
      savedPosition.current = data.position
      const element = videoRef.current
      if (element && Number.isFinite(element.duration) && data.position < element.duration && element.currentTime < 2) {
        element.currentTime = data.position
      }
    }).catch(() => {
      if (generation === requestGeneration.current) setProgressError('Saved playback position could not be loaded.')
    })
    return () => { requestGeneration.current += 1 }
  }, [user, contentType, contentId])

  const persist = useCallback(async (completed = false, force = false) => {
    if (!user || !contentId || !videoRef.current) return
    const element = videoRef.current
    const position = element.currentTime
    const now = Date.now()
    if (!force && position - lastSavedAt.current < 15) return
    lastSavedAt.current = position
    const payload = {
      content_type: contentType,
      content_id: contentId,
      position,
      duration: Number.isFinite(element.duration) ? element.duration : null,
      completed,
      watched_at: new Date(now).toISOString(),
    }
    if (saving.current) { queued.current = payload; return }
    saving.current = true
    let next = payload
    try {
      while (next) {
        queued.current = null
        await saveWatchProgress(next)
        next = queued.current
      }
      setProgressError('')
    } catch {
      setProgressError('Playback position could not be saved.')
    } finally { saving.current = false }
  }, [user, contentId, contentType])

  function togglePlayback() {
    const element = videoRef.current
    if (!element) return
    if (element.paused) void element.play().catch(() => setError('Playback could not start. Try pressing play again.'))
    else element.pause()
  }

  function seekBy(seconds) {
    const element = videoRef.current
    if (!element || !Number.isFinite(element.duration)) return
    element.currentTime = Math.max(0, Math.min(element.duration, element.currentTime + seconds))
  }

  function selectQuality(nextQuality) {
    const element = videoRef.current
    if (!element || nextQuality === quality) { setSettingsOpen(false); return }
    pendingSourceRestore.current = { time: element.currentTime, resume: !element.paused }
    setLoading(true)
    setError('')
    setSettingsOpen(false)
    setSettingsPage('main')
    setQuality(nextQuality)
  }

  function changePlaybackRate(rate) {
    if (videoRef.current) videoRef.current.playbackRate = rate
    setPlaybackRate(rate)
    setSettingsOpen(false)
    setSettingsPage('main')
  }

  async function toggleFullscreen() {
    const stage = stageRef.current
    const element = videoRef.current
    try {
      if (document.fullscreenElement) await document.exitFullscreen()
      else if (stage?.requestFullscreen) await stage.requestFullscreen()
      else if (element?.webkitEnterFullscreen) element.webkitEnterFullscreen()
    } catch {
      setError('Fullscreen is not available in this browser.')
    }
  }

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.altKey || event.ctrlKey || event.metaKey || /INPUT|TEXTAREA|SELECT|BUTTON/.test(event.target?.tagName || '')) return
      if (!stageRef.current?.contains(event.target) && event.target !== document.body) return
      if (event.code === 'Space') { event.preventDefault(); togglePlayback() }
      if (event.key === 'ArrowLeft') { event.preventDefault(); seekBy(-10) }
      if (event.key === 'ArrowRight') { event.preventDefault(); seekBy(10) }
      if (event.key.toLowerCase() === 'm' && videoRef.current) setMuted((value) => { videoRef.current.muted = !value; return !value })
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  })

  useEffect(() => {
    function syncFullscreen() { setFullscreen(document.fullscreenElement === stageRef.current) }
    document.addEventListener('fullscreenchange', syncFullscreen)
    return () => document.removeEventListener('fullscreenchange', syncFullscreen)
  }, [])

  if (!video?.secure_url) return <p className="movie-state">Video is not available yet.</p>

  function handleMetadata() {
    const element = videoRef.current
    if (!element) return
    setLoading(false)
    setError('')
    setDuration(Number.isFinite(element.duration) ? element.duration : 0)
    const sourceRestore = pendingSourceRestore.current
    const target = sourceRestore?.time ?? savedPosition.current
    if (Number.isFinite(target) && target > 0 && target < element.duration) {
      element.currentTime = target
      savedPosition.current = null
    }
    if (sourceRestore?.resume) void element.play().catch(() => {})
    pendingSourceRestore.current = null
  }

  function handleVolumeChange(event) {
    const nextVolume = Number(event.target.value)
    setVolume(nextVolume)
    setMuted(nextVolume === 0)
    if (videoRef.current) {
      videoRef.current.volume = nextVolume
      videoRef.current.muted = nextVolume === 0
    }
  }

  const VolumeIcon = muted || volume === 0 ? faVolumeXmark : volume < 0.5 ? faVolumeLow : faVolumeHigh

  return <section
    className="video-player"
    ref={stageRef}
    tabIndex={0}
    aria-label={`${title} video player`}
    onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setSettingsOpen(false) }}
  >
    <video
      ref={videoRef}
      src={source}
      playsInline
      preload="metadata"
      poster={poster?.secure_url || undefined}
      onClick={togglePlayback}
      onLoadedMetadata={handleMetadata}
      onCanPlay={() => { setLoading(false); setError('') }}
      onWaiting={() => setLoading(true)}
      onPlaying={() => { setLoading(false); setPlaying(true) }}
      onPause={() => { setPlaying(false); void persist(false, true) }}
      onTimeUpdate={() => { setCurrentTime(videoRef.current?.currentTime || 0); void persist() }}
      onDurationChange={() => setDuration(Number.isFinite(videoRef.current?.duration) ? videoRef.current.duration : 0)}
      onVolumeChange={() => { if (videoRef.current) { setMuted(videoRef.current.muted); setVolume(videoRef.current.volume) } }}
      onEnded={() => { setPlaying(false); void persist(true, true) }}
      onError={() => { setLoading(false); setError('This video could not be played. Please try again later.') }}
      aria-label={title}
    >
      Your browser does not support HTML video.
    </video>

    {!playing && !loading && !error && <button className="video-player-center-play" type="button" aria-label="Play video" onClick={togglePlayback}><FontAwesomeIcon icon={faPlay} /></button>}
    {loading && !error && <div className="video-player-overlay-state" role="status">Loading video…</div>}
    {error && <div className="video-player-overlay-state video-player-error" role="alert">{error}</div>}
    {progressError && <p className="video-player-progress-error" role="status">{progressError}</p>}

    <div className="video-player-controls" onClick={(event) => event.stopPropagation()}>
      <input
        className="video-player-seek"
        type="range"
        min="0"
        max={duration || 0}
        step="0.1"
        value={Math.min(currentTime, duration || currentTime)}
        style={{ '--seek-progress': `${seekPercent}%` }}
        aria-label="Seek video"
        onChange={(event) => {
          const nextTime = Number(event.target.value)
          if (videoRef.current) videoRef.current.currentTime = nextTime
          setCurrentTime(nextTime)
        }}
      />
      <div className="video-player-control-row">
        <div className="video-player-control-group">
          <button className="video-control-button" type="button" aria-label={playing ? 'Pause video' : 'Play video'} onClick={togglePlayback}><FontAwesomeIcon icon={playing ? faPause : faPlay} /></button>
          <button className="video-control-button video-skip-button" type="button" aria-label="Back 10 seconds" onClick={() => seekBy(-10)}><FontAwesomeIcon icon={faRotateLeft} /><span>10</span></button>
          <button className="video-control-button video-skip-button" type="button" aria-label="Forward 10 seconds" onClick={() => seekBy(10)}><FontAwesomeIcon icon={faRotateRight} /><span>10</span></button>
          <span className="video-player-time"><strong>{formatTime(currentTime)}</strong> / {formatTime(duration)}</span>
        </div>
        <div className="video-player-control-group">
          <div className="video-volume-control">
            <button className="video-control-button" type="button" aria-label={muted ? 'Unmute' : 'Mute'} onClick={() => {
              const next = !muted
              setMuted(next)
              if (videoRef.current) videoRef.current.muted = next
            }}><FontAwesomeIcon icon={VolumeIcon} /></button>
            <input type="range" min="0" max="1" step="0.05" value={muted ? 0 : volume} aria-label="Volume" onChange={handleVolumeChange} />
          </div>
          <div className="video-settings-wrap">
            <button className="video-control-button" type="button" aria-label="Playback settings" aria-expanded={settingsOpen} onClick={() => { setSettingsOpen((value) => !value); setSettingsPage('main') }}><FontAwesomeIcon icon={faGear} /></button>
            {settingsOpen && <div className="video-settings-menu" role="dialog" aria-label="Playback settings">
              {settingsPage === 'main' ? <>
                {hasQualityOptions && <button type="button" onClick={() => setSettingsPage('quality')}><span>Quality</span><strong>{quality} <span aria-hidden="true">›</span></strong></button>}
                <button type="button" onClick={() => setSettingsPage('speed')}><span>Playback speed</span><strong>{playbackRate === 1 ? 'Normal' : `${playbackRate}×`} <span aria-hidden="true">›</span></strong></button>
              </> : <>
                <button className="video-settings-back" type="button" onClick={() => setSettingsPage('main')}><span aria-hidden="true">‹</span> {settingsPage === 'quality' ? 'Video quality' : 'Playback speed'}</button>
                {settingsPage === 'quality' && <>
                  <button type="button" aria-pressed={quality === 'Auto'} onClick={() => selectQuality('Auto')}>Auto <span>{quality === 'Auto' ? '✓' : ''}</span></button>
                  {QUALITY_LEVELS.map(({ label }) => <button key={label} type="button" aria-pressed={quality === label} onClick={() => selectQuality(label)}>{label} <span>{quality === label ? '✓' : ''}</span></button>)}
                </>}
                {settingsPage === 'speed' && PLAYBACK_RATES.map((rate) => <button key={rate} type="button" aria-pressed={playbackRate === rate} onClick={() => changePlaybackRate(rate)}>{rate === 1 ? 'Normal' : `${rate}×`} <span>{playbackRate === rate ? '✓' : ''}</span></button>)}
              </>}
            </div>}
          </div>
          <button className="video-control-button" type="button" aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'} onClick={() => void toggleFullscreen()}><FontAwesomeIcon icon={fullscreen ? faCompress : faExpand} /></button>
        </div>
      </div>
    </div>
  </section>
}
