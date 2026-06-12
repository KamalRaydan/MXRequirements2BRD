import { create } from 'zustand'
import { apiDelete, apiGet, apiPatch, apiPost, processSource, refreshSourceDates, uploadBranding, uploadSource } from '../api'

export const useProjectStore = create((set, get) => ({
  projects: [],
  current: null, // full project incl. source_count + latest_run
  sources: [],
  runs: [],
  branding: { branded_docx_path: null, headings: [] },

  async loadProjects() {
    set({ projects: await apiGet('/projects') })
  },

  async createProject(fields) {
    const project = await apiPost('/projects', fields)
    await get().loadProjects()
    return project
  },

  async deleteProject(id) {
    await apiDelete(`/projects/${id}`)
    await get().loadProjects()
  },

  async loadProject(id) {
    const [current, sources, runs, branding] = await Promise.all([
      apiGet(`/projects/${id}`),
      apiGet(`/projects/${id}/sources`),
      apiGet(`/projects/${id}/runs`),
      apiGet(`/projects/${id}/branding`),
    ])
    set({ current, sources, runs, branding })
  },

  async refreshSources(id) {
    set({ sources: await apiGet(`/projects/${id}/sources`) })
  },

  async uploadFiles(projectId, files) {
    for (const file of files) {
      await uploadSource(projectId, file)
    }
    await get().refreshSources(projectId)
  },

  async deleteSource(projectId, sourceId) {
    await apiDelete(`/projects/${projectId}/sources/${sourceId}`)
    await get().refreshSources(projectId)
  },

  // Re-run extraction/transcription for a PENDING (pre-M5) or ERROR source
  async processSource(projectId, sourceId) {
    await processSource(projectId, sourceId)
    await get().refreshSources(projectId)
  },

  // Pass null to clear the override and fall back to the source timestamp
  async setSourceDate(projectId, sourceId, isoDateOrNull) {
    await apiPatch(`/projects/${projectId}/sources/${sourceId}`, {
      user_timestamp_override: isoDateOrNull,
    })
    await get().refreshSources(projectId)
  },

  // Re-reads embedded document dates for sources uploaded before date
  // extraction existed; the route returns the refreshed list
  async refreshDates(projectId) {
    set({ sources: await refreshSourceDates(projectId) })
  },

  async setBranding(projectId, file) {
    const branding = await uploadBranding(projectId, file)
    set({ branding })
  },

  async removeBranding(projectId) {
    await apiDelete(`/projects/${projectId}/branding`)
    set({ branding: { branded_docx_path: null, headings: [] } })
  },
}))
