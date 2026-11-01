import { useCallback, useEffect, useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowDown, faArrowLeft, faArrowRight, faArrowUp, faPen, faStar, faTrash } from '@fortawesome/free-solid-svg-icons'
import { Link } from 'react-router-dom'
import { createAdminEpisode, createAdminSeason, createAdminSeries, deleteAdminEpisode, deleteAdminSeason, deleteAdminSeries, getAdminEpisodes, getAdminSeasons, getAdminSeries, reorderAdminEpisodes, reorderAdminSeasons, updateAdminEpisode, updateAdminSeason, updateAdminSeries } from '../services/series.js'
import { createRequestGuard } from '../features/requestGuard.js'
import { nextPage, previousPage } from '../features/pagination.js'
import MediaUploader from '../components/MediaUploader.jsx'

const blankSeries = { title: '', slug: '', short_description: '', description: '', release_year: new Date().getFullYear(), genres: '', language: '', content_rating: 'NR', cast: '', director: '', production_company: '', country: '', status: 'draft', is_featured: false, poster_url: '', backdrop_url: '' }
const blankEpisode = { title: '', description: '', duration: 40, status: 'draft', is_free: false, release_date: '' }
const formOfSeries = (series) => series ? ({ ...series, genres: (series.genres || []).join(', '), cast: (series.cast || []).join(', ') }) : { ...blankSeries }
const errorMessage = (error) => error.response?.data?.detail || Object.values(error.response?.data?.errors || {}).flat().join(' ') || 'The change could not be saved.'

export default function AdminSeriesPage() {
  const [pageData, setPageData] = useState({ results: [], page: 1, pages: 0, total: 0 })
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(blankSeries)
  const [selected, setSelected] = useState(null)
  const [seasons, setSeasons] = useState([])
  const [episodes, setEpisodes] = useState([])
  const [specials, setSpecials] = useState([])
  const [season, setSeason] = useState(null)
  const [seasonForm, setSeasonForm] = useState({ title: '', description: '', release_year: '' })
  const [episodeForm, setEpisodeForm] = useState(blankEpisode)
  const [specialForm, setSpecialForm] = useState(blankEpisode)
  const [editingSeasonId, setEditingSeasonId] = useState(null)
  const [seasonEditForm, setSeasonEditForm] = useState(null)
  const [editingEpisodeId, setEditingEpisodeId] = useState(null)
  const [episodeEditForm, setEpisodeEditForm] = useState(null)
  const [loading, setLoading] = useState(true)
  const [childLoading, setChildLoading] = useState(false)
  const [episodeLoading, setEpisodeLoading] = useState(false)
  const [error, setError] = useState('')
  const [childError, setChildError] = useState('')
  const [episodeError, setEpisodeError] = useState('')
  const [notice, setNotice] = useState('')
  const listRequest = useRef(null)
  const childRequest = useRef(null)
  const episodeRequest = useRef(null)
  const childController = useRef(null)
  const episodeController = useRef(null)
  if (!listRequest.current) listRequest.current = createRequestGuard()
  if (!childRequest.current) childRequest.current = createRequestGuard()
  if (!episodeRequest.current) episodeRequest.current = createRequestGuard()

  const load = useCallback(() => {
    const token = listRequest.current.begin()
    setLoading(true)
    getAdminSeries({ page, page_size: 20, sort: '-created_at' }).then(({ data }) => {
      if (!listRequest.current.isCurrent(token)) return
      setPageData(data)
      if (data.pages > 0 && page > data.pages) setPage(data.pages)
      setError('')
    }).catch((requestError) => {
      if (listRequest.current.isCurrent(token)) setError(errorMessage(requestError))
    }).finally(() => {
      if (listRequest.current.isCurrent(token)) setLoading(false)
    })
  }, [page])

  useEffect(() => {
    load()
    return () => listRequest.current.invalidate()
  }, [load])

  useEffect(() => () => {
    childController.current?.abort()
    episodeController.current?.abort()
    childRequest.current.invalidate()
    episodeRequest.current.invalidate()
  }, [])

  async function selectSeries(item) {
    childController.current?.abort()
    episodeController.current?.abort()
    episodeRequest.current.invalidate()
    const token = childRequest.current.begin()
    const controller = new AbortController()
    childController.current = controller
    setSelected(item)
    setSeason(null)
    setSeasons([])
    setEpisodes([])
    setSpecials([])
    setChildError('')
    setEpisodeError('')
    setChildLoading(true)
    try {
      const [seasonResponse, specialResponse] = await Promise.all([
        getAdminSeasons(item.id, { signal: controller.signal }),
        getAdminEpisodes(item.id, null, { signal: controller.signal }),
      ])
      if (!childRequest.current.isCurrent(token)) return
      setSeasons(seasonResponse.data)
      setSpecials(specialResponse.data)
    } catch (requestError) {
      if (childRequest.current.isCurrent(token) && requestError.name !== 'CanceledError') setChildError(errorMessage(requestError))
    } finally {
      if (childRequest.current.isCurrent(token)) setChildLoading(false)
    }
  }

  async function selectSeason(item) {
    episodeController.current?.abort()
    const token = episodeRequest.current.begin()
    const controller = new AbortController()
    episodeController.current = controller
    setSeason(item)
    setEpisodes([])
    setEpisodeError('')
    setEpisodeLoading(true)
    try {
      const response = await getAdminEpisodes(selected.id, item.id, { signal: controller.signal })
      if (episodeRequest.current.isCurrent(token)) setEpisodes(response.data)
    } catch (requestError) {
      if (episodeRequest.current.isCurrent(token) && requestError.name !== 'CanceledError') setEpisodeError(errorMessage(requestError))
    } finally {
      if (episodeRequest.current.isCurrent(token)) setEpisodeLoading(false)
    }
  }

  function changeSeriesForm(event) {
    const { name, value, type, checked } = event.target
    setForm((current) => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
  }

  async function saveSeries(event) {
    event.preventDefault()
    setError('')
    try {
      const data = { ...form, release_year: Number(form.release_year), genres: form.genres.split(',').map((item) => item.trim()).filter(Boolean), cast: form.cast.split(',').map((item) => item.trim()).filter(Boolean) }
      if (editing) await updateAdminSeries(editing.id, data)
      else await createAdminSeries(data)
      setEditing(null)
      setForm({ ...blankSeries })
      setNotice(editing ? 'Series updated.' : 'Series created.')
      load()
    } catch (requestError) { setError(errorMessage(requestError)) }
  }

  async function toggleSeries(item, field, value) {
    try { await updateAdminSeries(item.id, { [field]: value }); setNotice(`${item.title} updated.`); load() }
    catch (requestError) { setError(errorMessage(requestError)) }
  }

  async function removeSeries(item) {
    if (!window.confirm(`Delete “${item.title}” and all its seasons and episodes?`)) return
    try {
      await deleteAdminSeries(item.id, item.slug)
      if (selected?.id === item.id) setSelected(null)
      setNotice('Series and its content deleted.')
      load()
    } catch (requestError) { setError(errorMessage(requestError)) }
  }

  async function addSeason(event) {
    event.preventDefault()
    try {
      await createAdminSeason(selected.id, { title: seasonForm.title, description: seasonForm.description, release_year: seasonForm.release_year ? Number(seasonForm.release_year) : null, status: 'draft' })
      setSeasonForm({ title: '', description: '', release_year: '' })
      await selectSeries(selected)
      setNotice('Season created.')
    } catch (requestError) { setChildError(errorMessage(requestError)) }
  }

  function beginSeasonEdit(item) {
    setEditingSeasonId(item.id)
    setSeasonEditForm({ title: item.title, description: item.description || '', release_year: item.release_year ?? '', status: item.status })
  }

  async function saveSeasonEdit(event) {
    event.preventDefault()
    try {
      await updateAdminSeason(selected.id, editingSeasonId, { ...seasonEditForm, release_year: seasonEditForm.release_year === '' ? null : Number(seasonEditForm.release_year) })
      setEditingSeasonId(null)
      await selectSeries(selected)
      setNotice('Season updated.')
    } catch (requestError) { setChildError(errorMessage(requestError)) }
  }

  async function seasonStatus(item) {
    try { await updateAdminSeason(selected.id, item.id, { status: item.status === 'published' ? 'draft' : 'published' }); await selectSeries(selected); setNotice('Season status updated.') }
    catch (requestError) { setChildError(errorMessage(requestError)) }
  }

  async function removeSeason(item) {
    if (!window.confirm(`Delete ${item.title} and its episodes?`)) return
    try { await deleteAdminSeason(selected.id, item.id); setSeason(null); setEpisodes([]); await selectSeries(selected); setNotice('Season and its episodes deleted.') }
    catch (requestError) { setChildError(errorMessage(requestError)) }
  }

  async function addEpisode(event, isSpecial = false) {
    event.preventDefault()
    const seasonId = isSpecial ? null : season?.id
    if (!isSpecial && !seasonId) return
    const values = isSpecial ? specialForm : episodeForm
    try {
      await createAdminEpisode(selected.id, { ...values, duration: Number(values.duration), release_date: values.release_date || null }, seasonId)
      if (isSpecial) setSpecialForm({ ...blankEpisode })
      else setEpisodeForm({ ...blankEpisode })
      if (isSpecial) setSpecials((await getAdminEpisodes(selected.id)).data)
      else await selectSeason(season)
      setNotice(isSpecial ? 'Special episode created.' : 'Episode created.')
    } catch (requestError) { if (isSpecial) setChildError(errorMessage(requestError)); else setEpisodeError(errorMessage(requestError)) }
  }

  function beginEpisodeEdit(item) {
    setEditingEpisodeId(item.id)
    setEpisodeEditForm({ title: item.title, description: item.description || '', duration: item.duration, is_free: item.is_free, release_date: item.release_date || '' })
  }

  async function saveEpisodeEdit(event, item) {
    event.preventDefault()
    try {
      await updateAdminEpisode(selected.id, item.id, { ...episodeEditForm, duration: Number(episodeEditForm.duration), release_date: episodeEditForm.release_date || null })
      setEditingEpisodeId(null)
      if (item.type === 'regular') await selectSeason(season)
      else setSpecials((await getAdminEpisodes(selected.id)).data)
      setNotice('Episode updated.')
    } catch (requestError) { if (item.type === 'regular') setEpisodeError(errorMessage(requestError)); else setChildError(errorMessage(requestError)) }
  }

  async function toggleEpisode(item) {
    try {
      await updateAdminEpisode(selected.id, item.id, { status: item.status === 'published' ? 'draft' : 'published' })
      if (item.type === 'regular') await selectSeason(season)
      else setSpecials((await getAdminEpisodes(selected.id)).data)
    } catch (requestError) { if (item.type === 'regular') setEpisodeError(errorMessage(requestError)); else setChildError(errorMessage(requestError)) }
  }

  async function removeEpisode(item) {
    try {
      await deleteAdminEpisode(selected.id, item.id)
      if (item.type === 'regular') await selectSeason(season)
      else setSpecials((await getAdminEpisodes(selected.id)).data)
    } catch (requestError) { if (item.type === 'regular') setEpisodeError(errorMessage(requestError)); else setChildError(errorMessage(requestError)) }
  }

  async function moveSeason(index, delta) {
    const ordered = [...seasons]
    const target = index + delta
    if (target < 0 || target >= ordered.length) return
    ;[ordered[index], ordered[target]] = [ordered[target], ordered[index]]
    try { await reorderAdminSeasons(selected.id, ordered.map((item) => item.id)); await selectSeries(selected) }
    catch (requestError) { setChildError(errorMessage(requestError)) }
  }

  async function moveEpisode(items, index, delta, isSpecial) {
    const ordered = [...items]
    const target = index + delta
    if (target < 0 || target >= ordered.length) return
    ;[ordered[index], ordered[target]] = [ordered[target], ordered[index]]
    try {
      await reorderAdminEpisodes(selected.id, ordered.map((item) => item.id), isSpecial ? null : season?.id)
      if (isSpecial) setSpecials(ordered.map((item, number) => ({ ...item, special_number: number + 1 })))
      else setEpisodes(ordered.map((item, number) => ({ ...item, episode_number: number + 1 })))
    } catch (requestError) { if (isSpecial) setChildError(errorMessage(requestError)); else setEpisodeError(errorMessage(requestError)) }
  }

  const changePage = (transition) => setPage((current) => transition(current, pageData.pages))
  const editEpisodeForm = (item) => <form className="series-edit-form" onSubmit={(event) => void saveEpisodeEdit(event, item)}>
    <label>Title<input value={episodeEditForm.title} onChange={(event) => setEpisodeEditForm({ ...episodeEditForm, title: event.target.value })} required /></label>
    <label>Description<textarea value={episodeEditForm.description} onChange={(event) => setEpisodeEditForm({ ...episodeEditForm, description: event.target.value })} /></label>
    <label>Duration (minutes)<input type="number" min="1" max="1000" value={episodeEditForm.duration} onChange={(event) => setEpisodeEditForm({ ...episodeEditForm, duration: event.target.value })} required /></label>
    <label>Release date<input type="date" value={episodeEditForm.release_date} onChange={(event) => setEpisodeEditForm({ ...episodeEditForm, release_date: event.target.value })} /></label>
    <label className="movie-featured-toggle"><input type="checkbox" checked={episodeEditForm.is_free} onChange={(event) => setEpisodeEditForm({ ...episodeEditForm, is_free: event.target.checked })} /> Free episode</label>
    <div className="series-form-actions"><button className="primary-button">Save episode</button><button className="quiet-button" type="button" onClick={() => setEditingEpisodeId(null)}>Cancel</button></div>
  </form>

  return <section className="admin-movies-page">
    <div className="admin-page-heading"><div><span className="eyebrow">CINESPLIT · STUDIO</span><h1>Series management</h1><p>Build the next story worth following.</p></div><Link className="quiet-button" to="/series">View series catalog</Link></div>
    {notice && <p className="form-notice" role="status">{notice}</p>}{error && <p className="form-alert" role="alert">{error}</p>}
    <form className="movie-editor" onSubmit={saveSeries}><div className="movie-editor-heading"><div><span className="eyebrow">{editing ? 'EDIT SERIES' : 'ADD TO THE LIBRARY'}</span><h2>{editing ? editing.title : 'Create a series'}</h2></div>{editing && <button className="quiet-button" type="button" onClick={() => { setEditing(null); setForm({ ...blankSeries }) }}>Cancel</button>}</div>
      <div className="movie-editor-grid">{[['title','Title'],['slug','Slug'],['release_year','Release year'],['genres','Genres · comma separated'],['language','Language'],['content_rating','Content rating'],['director','Director'],['production_company','Production company'],['country','Country'],['cast','Cast · comma separated'],['poster_url','Poster URL'],['backdrop_url','Backdrop URL']].map(([name,label]) => <label key={name}>{label}<input name={name} value={form[name] ?? ''} onChange={changeSeriesForm} required={['title','release_year','genres'].includes(name)} /></label>)}
        <label className="movie-editor-wide">Short description<input name="short_description" value={form.short_description} onChange={changeSeriesForm} /></label><label className="movie-editor-wide">Description<textarea name="description" value={form.description} onChange={changeSeriesForm} /></label><label>Status<select name="status" value={form.status} onChange={changeSeriesForm}><option value="draft">Draft</option><option value="published">Published</option></select></label><label className="movie-featured-toggle"><input type="checkbox" name="is_featured" checked={form.is_featured} onChange={changeSeriesForm} /> Featured</label>
      </div><button className="primary-button" type="submit">{editing ? 'Save series' : 'Create series'}</button>
    </form>

    <section className="admin-movie-list"><div className="admin-list-heading"><div><h2>Series library <span className="admin-count">{pageData.total}</span></h2></div></div>
      {loading ? <p role="status" className="movie-state">Loading series…</p> : !pageData.results.length ? <p className="movie-state">No series in this view.</p> : <div className="admin-movie-table-wrap"><table className="admin-movie-table"><thead><tr><th>Series</th><th>Year</th><th>Status</th><th>Actions</th></tr></thead><tbody>{pageData.results.map((item) => <tr key={item.id}><td><button className="series-select-button" onClick={() => void selectSeries(item)}>{item.title}</button><small>{item.slug}</small></td><td>{item.release_year}</td><td><span className={`movie-status status-${item.status}`}>{item.status}</span></td><td className="admin-row-actions"><button className="icon-button" onClick={() => { setEditing(item); setForm(formOfSeries(item)) }} aria-label={`Edit ${item.title}`}><FontAwesomeIcon icon={faPen} /></button><button className="icon-button" onClick={() => void toggleSeries(item, 'is_featured', !item.is_featured)} aria-label={`Toggle featured ${item.title}`}><FontAwesomeIcon icon={faStar} /></button><button className="icon-button" onClick={() => void toggleSeries(item, 'status', item.status === 'published' ? 'draft' : 'published')}>{item.status === 'published' ? 'Unpublish' : 'Publish'}</button><button className="icon-button danger-icon" onClick={() => void removeSeries(item)} aria-label={`Delete ${item.title}`}><FontAwesomeIcon icon={faTrash} /></button></td></tr>)}</tbody></table></div>}
      {pageData.pages > 1 && <nav className="movie-pagination" aria-label="Admin series pages"><button className="quiet-button" type="button" disabled={loading || page <= 1} onClick={() => changePage(previousPage)}><FontAwesomeIcon icon={faArrowLeft} /> Previous</button><span>Page {pageData.page} of {pageData.pages}</span><button className="quiet-button" type="button" disabled={loading || page >= pageData.pages} onClick={() => changePage(nextPage)}>Next <FontAwesomeIcon icon={faArrowRight} /></button></nav>}
    </section>

    {selected && <section className="admin-movie-list series-admin-children"><div className="series-section-heading"><div><span className="eyebrow">CONTENT STRUCTURE</span><h2>{selected.title}</h2></div><button className="quiet-button" onClick={() => setSelected(null)}>Close</button></div>
      {childError && <p className="form-alert" role="alert">{childError}</p>}
      {childLoading ? <p className="movie-state" role="status">Loading seasons and specials…</p> : <>
        <div className="series-admin-columns"><div><h3>Seasons</h3>
          {!seasons.length && <p className="movie-state">No seasons yet.</p>}
          {seasons.map((item,index) => <div key={item.id}><div className="series-admin-item"><span>{item.season_number}. {item.title} <small className={`movie-status status-${item.status}`}>{item.status}</small></span><span className="admin-row-actions"><button className="icon-button" aria-label={`Edit ${item.title}`} onClick={() => beginSeasonEdit(item)}><FontAwesomeIcon icon={faPen} /></button><button className="icon-button" aria-label="Move season up" disabled={index === 0} onClick={() => void moveSeason(index,-1)}><FontAwesomeIcon icon={faArrowUp} /></button><button className="icon-button" aria-label="Move season down" disabled={index === seasons.length - 1} onClick={() => void moveSeason(index,1)}><FontAwesomeIcon icon={faArrowDown} /></button><button className="icon-button" onClick={() => void seasonStatus(item)}>{item.status === 'published' ? 'Unpublish' : 'Publish'}</button><button className="icon-button danger-icon" onClick={() => void removeSeason(item)} aria-label={`Delete ${item.title}`}><FontAwesomeIcon icon={faTrash} /></button><button className="quiet-button" onClick={() => void selectSeason(item)}>Manage episodes</button></span></div>
            {editingSeasonId === item.id && <form className="series-edit-form" onSubmit={saveSeasonEdit}><label>Title<input value={seasonEditForm.title} onChange={(event) => setSeasonEditForm({ ...seasonEditForm, title: event.target.value })} required /></label><label>Description<textarea value={seasonEditForm.description} onChange={(event) => setSeasonEditForm({ ...seasonEditForm, description: event.target.value })} /></label><label>Release year<input type="number" min="1870" max="2100" value={seasonEditForm.release_year} onChange={(event) => setSeasonEditForm({ ...seasonEditForm, release_year: event.target.value })} /></label><label>Status<select value={seasonEditForm.status} onChange={(event) => setSeasonEditForm({ ...seasonEditForm, status: event.target.value })}><option value="draft">Draft</option><option value="published">Published</option></select></label><div className="series-form-actions"><button className="primary-button">Save season</button><button className="quiet-button" type="button" onClick={() => setEditingSeasonId(null)}>Cancel</button></div></form>}
          </div>)}
          <form className="series-inline-form" onSubmit={addSeason}><input placeholder="Season title" value={seasonForm.title} onChange={(event) => setSeasonForm({ ...seasonForm, title: event.target.value })} required /><input placeholder="Description" value={seasonForm.description} onChange={(event) => setSeasonForm({ ...seasonForm, description: event.target.value })} /><input type="number" min="1870" max="2100" aria-label="Season release year" placeholder="Release year" value={seasonForm.release_year} onChange={(event) => setSeasonForm({ ...seasonForm, release_year: event.target.value })} /><button className="primary-button">Add season</button></form>
        </div></div>

        <div className="series-admin-columns"><div><h3>{season ? `Episodes · ${season.title}` : 'Choose a season'}</h3>{season && <>
          <form className="series-inline-form" onSubmit={(event) => void addEpisode(event)}><input placeholder="Episode title" value={episodeForm.title} onChange={(event) => setEpisodeForm({ ...episodeForm, title: event.target.value })} required /><input type="number" min="1" max="1000" aria-label="Duration in minutes" value={episodeForm.duration} onChange={(event) => setEpisodeForm({ ...episodeForm, duration: event.target.value })} /><input type="date" aria-label="Episode release date" value={episodeForm.release_date} onChange={(event) => setEpisodeForm({ ...episodeForm, release_date: event.target.value })} /><button className="primary-button">Add episode</button></form>
          <label className="movie-featured-toggle"><input type="checkbox" checked={episodeForm.is_free} onChange={(event) => setEpisodeForm({ ...episodeForm, is_free: event.target.checked })} /> Free episode</label>
          {episodeLoading ? <p role="status" className="movie-state">Loading episodes…</p> : episodeError ? <p role="alert" className="form-alert">{episodeError}</p> : !episodes.length ? <p className="movie-state">No episodes in this season yet.</p> : episodes.map((item,index) => <div key={item.id}><div className="series-admin-item"><span>{item.episode_number}. {item.title} · {item.duration} min</span><span className="admin-row-actions"><button className="icon-button" aria-label="Move episode up" disabled={index === 0} onClick={() => void moveEpisode(episodes,index,-1,false)}><FontAwesomeIcon icon={faArrowUp} /></button><button className="icon-button" aria-label="Move episode down" disabled={index === episodes.length - 1} onClick={() => void moveEpisode(episodes,index,1,false)}><FontAwesomeIcon icon={faArrowDown} /></button><button className="icon-button" aria-label={`Edit ${item.title}`} onClick={() => beginEpisodeEdit(item)}><FontAwesomeIcon icon={faPen} /></button><button className="icon-button" onClick={() => void toggleEpisode(item)}>{item.status === 'published' ? 'Unpublish' : 'Publish'}</button><button className="icon-button danger-icon" onClick={() => void removeEpisode(item)} aria-label={`Delete ${item.title}`}><FontAwesomeIcon icon={faTrash} /></button></span></div><MediaUploader contentType="episode" contentId={item.id}/>{editingEpisodeId === item.id && editEpisodeForm(item)}</div>)}</>}</div>
          <div className="special-admin"><h3>Special episodes</h3><form className="series-inline-form" onSubmit={(event) => void addEpisode(event,true)}><input placeholder="Special episode title" value={specialForm.title} onChange={(event) => setSpecialForm({ ...specialForm, title: event.target.value })} required /><input type="number" min="1" max="1000" aria-label="Special duration in minutes" value={specialForm.duration} onChange={(event) => setSpecialForm({ ...specialForm, duration: event.target.value })} /><input type="date" aria-label="Special release date" value={specialForm.release_date} onChange={(event) => setSpecialForm({ ...specialForm, release_date: event.target.value })} /><button className="primary-button">Add special</button></form><label className="movie-featured-toggle"><input type="checkbox" checked={specialForm.is_free} onChange={(event) => setSpecialForm({ ...specialForm, is_free: event.target.checked })} /> Free special</label>{!specials.length ? <p className="movie-state">No special episodes yet.</p> : specials.map((item,index) => <div key={item.id}><div className="series-admin-item"><span>Special {item.special_number}. {item.title}</span><span className="admin-row-actions"><button className="icon-button" aria-label="Move special up" disabled={index === 0} onClick={() => void moveEpisode(specials,index,-1,true)}><FontAwesomeIcon icon={faArrowUp} /></button><button className="icon-button" aria-label="Move special down" disabled={index === specials.length - 1} onClick={() => void moveEpisode(specials,index,1,true)}><FontAwesomeIcon icon={faArrowDown} /></button><button className="icon-button" aria-label={`Edit ${item.title}`} onClick={() => beginEpisodeEdit(item)}><FontAwesomeIcon icon={faPen} /></button><button className="icon-button" onClick={() => void toggleEpisode(item)}>{item.status === 'published' ? 'Unpublish' : 'Publish'}</button><button className="icon-button danger-icon" onClick={() => void removeEpisode(item)} aria-label={`Delete ${item.title}`}><FontAwesomeIcon icon={faTrash} /></button></span></div><MediaUploader contentType="episode" contentId={item.id}/>{editingEpisodeId === item.id && editEpisodeForm(item)}</div>)}</div>
        </div>
      </>}</section>}
  </section>
}
