// Single API access layer (spec §13.1 note): every page and store goes through
// this module. In Milestone 3 only this file changes to route through the
// Electron IPC bridge instead of fetch/EventSource.
const BASE = '/api'

async function handle(response) {
  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const message = data?.error?.message || `Request failed (${response.status})`
    throw new Error(message)
  }
  return data
}

export function apiGet(path) {
  return fetch(BASE + path).then(handle)
}

export function apiPost(path, body) {
  return fetch(BASE + path, {
    method: 'POST',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }).then(handle)
}

export function apiPatch(path, body) {
  return fetch(BASE + path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(handle)
}

export function apiDelete(path) {
  return fetch(BASE + path, { method: 'DELETE' }).then(handle)
}

export function uploadSource(projectId, file) {
  const form = new FormData()
  form.append('file', file)
  // Browser gives us the file's last-modified time — that becomes the source timestamp
  if (file.lastModified) {
    form.append('source_timestamp', new Date(file.lastModified).toISOString())
  }
  return fetch(`${BASE}/projects/${projectId}/sources/upload`, {
    method: 'POST',
    body: form,
  }).then(handle)
}

// Re-read each source file's embedded created/modified date from disk
export function refreshSourceDates(projectId) {
  return apiPost(`/projects/${projectId}/sources/refresh-dates`)
}

// (Re)process a media source that is PENDING (pre-M5 upload) or ERROR
export function processSource(projectId, sourceId) {
  return apiPost(`/projects/${projectId}/sources/${sourceId}/process`)
}

// Branded reference DOCX whose headings replace the default BRD structure
export function uploadBranding(projectId, file) {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${BASE}/projects/${projectId}/branding`, {
    method: 'PUT',
    body: form,
  }).then(handle)
}

export function cancelRun(runId) {
  return apiPost(`/pipeline/${runId}/cancel`)
}

// SSE pipeline progress. Returns the EventSource so callers can close it.
export function streamRun(runId, { onProgress, onDone, onError }) {
  const source = new EventSource(`${BASE}/pipeline/${runId}/stream`)
  source.addEventListener('progress', (e) => onProgress(JSON.parse(e.data)))
  source.addEventListener('done', (e) => {
    onDone(JSON.parse(e.data))
    source.close()
  })
  source.addEventListener('error', (e) => {
    // Server-sent "error" events carry data; transport errors don't
    if (e.data) onError(JSON.parse(e.data))
    source.close()
  })
  return source
}

export function downloadUrl(runId) {
  return `${BASE}/pipeline/${runId}/download`
}
