import { create } from 'zustand'
import { apiDelete, apiGet, apiPost, uploadSource } from '../api'

export const useProjectStore = create((set, get) => ({
  projects: [],
  current: null, // full project incl. source_count + latest_run
  sources: [],
  runs: [],

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
    const [current, sources, runs] = await Promise.all([
      apiGet(`/projects/${id}`),
      apiGet(`/projects/${id}/sources`),
      apiGet(`/projects/${id}/runs`),
    ])
    set({ current, sources, runs })
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
}))
