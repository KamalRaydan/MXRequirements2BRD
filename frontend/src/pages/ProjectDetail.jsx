import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import StatusBadge from '../components/StatusBadge'
import SourceTextModal from '../components/SourceTextModal'
import ConfirmDialog from '../components/ConfirmDialog'
import { downloadUrl } from '../api'
import { useProjectStore } from '../store/projectStore'
import { useSettingsStore } from '../store/settingsStore'

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

// The "view text" action wording reflects how the text was produced
function viewLabel(filetype) {
  if (filetype === 'image') return 'View AI reading'
  if (filetype === 'audio' || filetype === 'video') return 'View transcript'
  return 'View text'
}

// ISO timestamp -> "YYYY-MM-DDTHH:mm" in local time, for <input type="datetime-local">
function toLocalInputValue(iso) {
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function ProjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    current, sources, runs, branding, loadProject, refreshSources, uploadFiles,
    deleteSource, processSource, setSourceDate, refreshDates, setBranding, removeBranding,
  } = useProjectStore()
  const { configured, loaded, load } = useSettingsStore()
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [editingSourceId, setEditingSourceId] = useState(null)
  const [viewingSource, setViewingSource] = useState(null)
  // Holds { title, message, confirmLabel, onConfirm } while a confirm dialog is open.
  const [confirmState, setConfirmState] = useState(null)
  const [dateValue, setDateValue] = useState('')
  const [brandingError, setBrandingError] = useState(null)
  const [refreshingDates, setRefreshingDates] = useState(false)
  const fileInput = useRef(null)
  const brandingInput = useRef(null)

  useEffect(() => {
    loadProject(id)
    if (!loaded) load()
  }, [id])

  // While any source is still extracting or transcribing, refresh its status every 2s
  const processing = sources.some((s) =>
    s.processing_status === 'EXTRACTING' || s.processing_status === 'TRANSCRIBING')
  useEffect(() => {
    if (!processing) return
    const timer = setInterval(() => refreshSources(id), 2000)
    return () => clearInterval(timer)
  }, [processing, id])

  async function handleFiles(files) {
    if (!files?.length) return
    setUploading(true)
    setUploadError(null)
    try {
      await uploadFiles(id, Array.from(files))
    } catch (e) {
      setUploadError(e.message)
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function saveSourceDate(sourceId) {
    await setSourceDate(id, sourceId, dateValue ? new Date(dateValue).toISOString() : null)
    setEditingSourceId(null)
  }

  async function handleRefreshDates() {
    setRefreshingDates(true)
    try {
      await refreshDates(id)
    } finally {
      setRefreshingDates(false)
    }
  }

  async function handleBrandingFile(file) {
    if (!file) return
    setBrandingError(null)
    try {
      await setBranding(id, file)
    } catch (e) {
      setBrandingError(e.message)
    } finally {
      if (brandingInput.current) brandingInput.current.value = ''
    }
  }

  const readyCount = sources.filter((s) => s.processing_status === 'EXTRACTED').length
  const canGenerate = readyCount > 0 && configured

  if (!current || current.id !== id) {
    return <p className="text-slate-500">Loading…</p>
  }

  return (
    <div className="space-y-8">
      {/* Project metadata header */}
      <div>
        <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">← Projects</Link>
        <h1 className="mt-1 text-xl font-semibold">{current.project_name}</h1>
        <p className="text-sm text-slate-500">
          {current.client_name} · {current.project_date} · {current.maximo_version} ·{' '}
          <span className="font-mono text-xs">{current.folder_path}</span>
        </p>
      </div>

      {/* Sources */}
      <section>
        <h2 className="mb-3 text-base font-semibold">Requirement Sources</h2>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
          className={`rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
            dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-white'
          }`}
        >
          <p className="text-sm text-slate-600">
            Drag &amp; drop requirement sources here — documents (PDF, DOCX, TXT, MD, XLSX),
            recordings (MP3, WAV, M4A, MP4, MOV), and images (PNG, JPG)
          </p>
          <button
            onClick={() => fileInput.current?.click()}
            disabled={uploading}
            className="mt-3 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-40"
          >
            {uploading ? 'Uploading…' : 'Browse files'}
          </button>
          <input
            ref={fileInput}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
        {uploadError && <p className="mt-2 text-sm text-red-600">{uploadError}</p>}

        {sources.length > 0 && (
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">File</th>
                  <th className="px-4 py-2">Size</th>
                  <th className="px-4 py-2">Effective date</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-4 py-2 font-medium">{s.filename}</td>
                    <td className="px-4 py-2 text-slate-500">{formatBytes(s.file_size_bytes)}</td>
                    <td className="px-4 py-2 text-slate-500">
                      {editingSourceId === s.id ? (
                        <span className="flex items-center gap-2">
                          <input
                            type="datetime-local"
                            value={dateValue}
                            onChange={(e) => setDateValue(e.target.value)}
                            className="rounded border border-slate-300 px-2 py-1 text-xs"
                          />
                          <button onClick={() => saveSourceDate(s.id)} className="text-xs font-medium text-blue-600 hover:underline">
                            Save
                          </button>
                          {s.user_timestamp_override && (
                            <button
                              onClick={() => { setDateValue(''); setSourceDate(id, s.id, null).then(() => setEditingSourceId(null)) }}
                              className="text-xs text-slate-400 hover:text-slate-600"
                            >
                              Clear override
                            </button>
                          )}
                          <button onClick={() => setEditingSourceId(null)} className="text-xs text-slate-400 hover:text-slate-600">
                            Cancel
                          </button>
                        </span>
                      ) : (
                        <>
                          {new Date(s.user_timestamp_override || s.source_timestamp).toLocaleString()}
                          {s.user_timestamp_override && (
                            <span className="ml-1 text-xs text-slate-400">(edited)</span>
                          )}
                        </>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <StatusBadge status={s.processing_status} filetype={s.filetype} title={s.error_message} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      {(s.processing_status === 'PENDING' || s.processing_status === 'ERROR') &&
                        s.filetype !== 'unknown' && (
                          <button
                            onClick={() => processSource(id, s.id)}
                            className="mr-3 text-xs font-medium text-blue-600 hover:underline"
                          >
                            {s.processing_status === 'PENDING' ? 'Process' : 'Retry'}
                          </button>
                        )}
                      {s.processing_status === 'EXTRACTED' && (
                        <button
                          onClick={() => setViewingSource(s)}
                          className="mr-3 text-xs font-medium text-blue-600 hover:underline"
                        >
                          {viewLabel(s.filetype)}
                        </button>
                      )}
                      <button
                        onClick={() => {
                          setEditingSourceId(s.id)
                          setDateValue(toLocalInputValue(s.user_timestamp_override || s.source_timestamp))
                        }}
                        className="mr-3 text-xs text-slate-400 hover:text-slate-900"
                      >
                        Edit date
                      </button>
                      <button
                        onClick={() => setConfirmState({
                          title: 'Delete file',
                          message: `Delete "${s.filename}" from this project? This cannot be undone.`,
                          confirmLabel: 'Delete',
                          onConfirm: () => deleteSource(id, s.id),
                        })}
                        className="text-xs text-slate-400 hover:text-red-600"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {sources.length > 0 && (
          <div className="mt-2 flex items-start justify-between gap-4">
            <p className="text-xs text-slate-400">
              Effective dates are read from inside PDF, Word, and Excel files when available.
              Plain-text and media files have no embedded date — use Edit date to correct them,
              or upload them in the order they were written.
            </p>
            <button
              onClick={handleRefreshDates}
              disabled={refreshingDates}
              className="shrink-0 text-xs font-medium text-blue-600 hover:underline disabled:opacity-40"
            >
              {refreshingDates ? 'Refreshing…' : 'Re-read dates from files'}
            </button>
          </div>
        )}
      </section>

      {/* Branded template (Milestone 2) */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-semibold">Branded Template</h2>
            <p className="text-sm text-slate-500">
              {branding.branded_docx_path
                ? 'The BRD will follow this document’s heading structure.'
                : 'Optional: upload a client DOCX — its headings replace the default BRD structure.'}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => brandingInput.current?.click()}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              {branding.branded_docx_path ? 'Replace' : 'Upload DOCX'}
            </button>
            {branding.branded_docx_path && (
              <button
                onClick={() => setConfirmState({
                  title: 'Remove template',
                  message: 'Remove the branded template from this project?',
                  confirmLabel: 'Remove',
                  onConfirm: () => removeBranding(id),
                })}
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-500 hover:bg-slate-50"
              >
                Remove
              </button>
            )}
          </div>
          <input
            ref={brandingInput}
            type="file"
            accept=".docx"
            className="hidden"
            onChange={(e) => handleBrandingFile(e.target.files?.[0])}
          />
        </div>
        {brandingError && <p className="mt-2 text-sm text-red-600">{brandingError}</p>}
        {branding.headings.length > 0 && (
          <ul className="mt-4 rounded-md border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700">
            {branding.headings.map((h, i) => (
              <li key={i} style={{ paddingLeft: `${(h.level - 1) * 16}px` }}>
                {h.title}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Generate */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">Generate BRD</h2>
            <p className="text-sm text-slate-500">
              {readyCount} source{readyCount === 1 ? '' : 's'} ready
              {!configured && loaded && ' — configure your AI provider in Settings first'}
            </p>
          </div>
          <button
            onClick={() => navigate(`/projects/${id}/generate`)}
            disabled={!canGenerate}
            className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            Generate
          </button>
        </div>
      </section>

      {/* Run history */}
      {runs.length > 0 && (
        <section>
          <h2 className="mb-3 text-base font-semibold">Run History</h2>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Started</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Sources used</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-4 py-2">{new Date(r.started_at).toLocaleString()}</td>
                    <td className="px-4 py-2">
                      <span className={
                        r.status === 'DONE' ? 'text-green-700' :
                        r.status === 'FAILED' ? 'text-red-600' : 'text-amber-600'
                      }>
                        {r.status}
                      </span>
                      {r.error_message && <span className="ml-2 text-xs text-slate-400">{r.error_message}</span>}
                    </td>
                    <td className="px-4 py-2 text-slate-500">{r.sources_used_count}</td>
                    <td className="px-4 py-2 text-right">
                      {r.status === 'DONE' && (
                        <a href={downloadUrl(r.id)} className="text-xs font-medium text-blue-600 hover:underline">
                          Download
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {viewingSource && (
        <SourceTextModal
          projectId={id}
          source={viewingSource}
          onClose={() => setViewingSource(null)}
        />
      )}

      {confirmState && (
        <ConfirmDialog
          title={confirmState.title}
          message={confirmState.message}
          confirmLabel={confirmState.confirmLabel}
          onConfirm={() => { confirmState.onConfirm(); setConfirmState(null) }}
          onCancel={() => setConfirmState(null)}
        />
      )}
    </div>
  )
}
