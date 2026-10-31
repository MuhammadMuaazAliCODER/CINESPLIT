import { useCallback, useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowDown, faArrowUp, faPen, faPlus, faTrash } from '@fortawesome/free-solid-svg-icons'
import { createAdminChapter, deleteAdminChapter, getAdminChapters, reorderAdminChapters, updateAdminChapter } from '../services/chapters.js'

const blank = { title: '', slug: '', description: '', duration: '', status: 'draft', is_free: false }
const message = (error, fallback) => error.response?.data?.detail || Object.values(error.response?.data?.errors || {}).flat().join(' ') || fallback

export default function ChapterManagement({ movie }) {
  const [chapters, setChapters] = useState([])
  const [form, setForm] = useState(blank)
  const [editingId, setEditingId] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const load = useCallback(async () => {
    setLoading(true)
    try { const { data } = await getAdminChapters(movie.id); setChapters(data); setError('') }
    catch (e) { setError(message(e, 'Chapters could not be loaded.')) }
    finally { setLoading(false) }
  }, [movie.id])
  useEffect(() => { void load() }, [load])

  async function submit(event) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      const payload = { ...form, duration: Number(form.duration) }
      if (editingId) await updateAdminChapter(movie.id, editingId, payload)
      else await createAdminChapter(movie.id, payload)
      setNotice(editingId ? 'Chapter updated.' : 'Chapter added at the end of the list.')
      setEditingId(''); setForm(blank); await load()
    } catch (e) { setError(message(e, 'Chapter could not be saved.')) }
    finally { setSaving(false) }
  }
  async function publish(chapter) {
    try { await updateAdminChapter(movie.id, chapter.id, { status: chapter.status === 'published' ? 'draft' : 'published' }); await load() }
    catch (e) { setError(message(e, 'Chapter status could not be changed.')) }
  }
  async function remove(chapter) {
    if (!window.confirm(`Delete “${chapter.title}”? Remaining chapters will be renumbered.`)) return
    try { await deleteAdminChapter(movie.id, chapter.id); setNotice('Chapter deleted; remaining chapters were renumbered.'); await load() }
    catch (e) { setError(message(e, 'Chapter could not be deleted.')) }
  }
  function move(index, delta) {
    const target = index + delta
    if (target < 0 || target >= chapters.length) return
    setChapters((items) => { const next = [...items]; [next[index], next[target]] = [next[target], next[index]]; return next })
  }
  async function saveOrder() {
    setSaving(true)
    try { const { data } = await reorderAdminChapters(movie.id, chapters.map((chapter) => chapter.id)); setChapters(data); setNotice('Chapter order saved.') }
    catch (e) { setError(message(e, 'Chapter order could not be saved.')); await load() }
    finally { setSaving(false) }
  }
  function edit(chapter) {
    setEditingId(chapter.id)
    setForm({ title: chapter.title, slug: chapter.slug, description: chapter.description || '', duration: String(chapter.duration), status: chapter.status, is_free: chapter.is_free })
  }

  return <section className="chapter-admin" aria-labelledby="chapter-admin-title">
    <div className="chapter-section-heading"><div><span className="eyebrow">CHAPTERS</span><h2 id="chapter-admin-title">Manage chapters</h2><p>New chapters are added at the end; use the arrows to change order.</p></div></div>
    {notice && <p className="form-notice" role="status">{notice}</p>}{error && <p className="form-alert" role="alert">{error}</p>}
    <form className="chapter-editor" onSubmit={submit}>
      <h3>{editingId ? 'Edit chapter' : 'Add a chapter'}</h3>
      <div className="chapter-editor-grid">
        <label>Title<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} maxLength={180} required /></label>
        <label>Slug <span className="field-hint">Leave blank to generate</span><input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} maxLength={190} /></label>
        <label>Duration (minutes)<input type="number" min="1" max="1000" value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} required /></label>
        <label>Publication<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option value="draft">Draft</option><option value="published">Published</option></select></label>
        <label className="chapter-editor-wide">Description<textarea rows="3" maxLength={12000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
        <label className="chapter-free-toggle"><input type="checkbox" checked={form.is_free} onChange={(e) => setForm({ ...form, is_free: e.target.checked })} /> Available without restrictions</label>
      </div>
      <div className="chapter-form-actions"><button className="primary-button" disabled={saving}>{saving ? 'Saving…' : editingId ? 'Save chapter' : <><FontAwesomeIcon icon={faPlus} aria-hidden="true" /> Add chapter</>}</button>{editingId && <button className="quiet-button" type="button" onClick={() => { setEditingId(''); setForm(blank) }}>Cancel edit</button>}</div>
    </form>
    <div className="chapter-admin-list-heading"><h3>Chapter order <span className="admin-count">{chapters.length}</span></h3>{chapters.length > 1 && <button className="quiet-button" type="button" onClick={() => void saveOrder()} disabled={saving}>Save order</button>}</div>
    {loading ? <p className="movie-state" role="status">Loading chapters…</p> : !chapters.length ? <p className="movie-state">No chapters yet. Add the first chapter above.</p> : <ol className="chapter-admin-list">{chapters.map((chapter, index) => <li className="chapter-admin-card" key={chapter.id}>
      <div className="chapter-number">{index + 1}</div><div className="chapter-admin-copy"><strong>{chapter.title}</strong><p>{chapter.duration} min · {chapter.status} · {chapter.is_free ? 'Free' : 'Restricted'}</p>{chapter.description && <small>{chapter.description}</small>}</div>
      <div className="chapter-admin-actions"><button className="icon-button" type="button" aria-label={`Move ${chapter.title} up`} disabled={!index} onClick={() => move(index, -1)}><FontAwesomeIcon icon={faArrowUp} aria-hidden="true" /></button><button className="icon-button" type="button" aria-label={`Move ${chapter.title} down`} disabled={index === chapters.length - 1} onClick={() => move(index, 1)}><FontAwesomeIcon icon={faArrowDown} aria-hidden="true" /></button><button className="icon-button" type="button" aria-label={`Edit ${chapter.title}`} onClick={() => edit(chapter)}><FontAwesomeIcon icon={faPen} aria-hidden="true" /></button><button className="icon-button" type="button" onClick={() => void publish(chapter)}>{chapter.status === 'published' ? 'Unpublish' : 'Publish'} {chapter.title}</button><button className="icon-button danger-icon" type="button" aria-label={`Delete ${chapter.title}`} onClick={() => void remove(chapter)}><FontAwesomeIcon icon={faTrash} aria-hidden="true" /></button></div>
    </li>)}</ol>}
  </section>
}
