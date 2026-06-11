import { create } from 'zustand'
import { apiPost, streamRun } from '../api'

const initial = {
  runId: null,
  status: 'idle', // idle | running | done | failed
  percent: 0,
  stage: null,
  messages: [], // last few progress messages
  outputPath: null,
  errorMessage: null,
}

export const usePipelineStore = create((set, get) => ({
  ...initial,
  eventSource: null,

  reset() {
    get().eventSource?.close()
    set({ ...initial, eventSource: null })
  },

  async start(projectId) {
    get().reset()
    const { run_id } = await apiPost(`/projects/${projectId}/generate`)
    set({ runId: run_id, status: 'running', percent: 0 })
    get().attach(run_id)
    return run_id
  },

  attach(runId) {
    const source = streamRun(runId, {
      onProgress: (data) =>
        set((state) => ({
          percent: data.percent,
          stage: data.stage,
          messages: [...state.messages, data.message].slice(-5),
        })),
      onDone: (data) => set({ status: 'done', percent: 100, outputPath: data.output_path }),
      onError: (data) => set({ status: 'failed', errorMessage: data.message }),
    })
    set({ runId, status: 'running', eventSource: source })
  },
}))
