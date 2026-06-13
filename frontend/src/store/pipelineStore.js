import { create } from 'zustand'
import { apiPost, cancelRun, streamRun } from '../api'

const initial = {
  runId: null,
  status: 'idle', // idle | running | cancelling | done | failed | cancelled
  percent: 0,
  stage: null,
  startedAt: null, // ISO time the run kicked off, shown on the Generate page
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
    set({ runId: run_id, status: 'running', percent: 0, startedAt: new Date().toISOString() })
    get().attach(run_id)
    return run_id
  },

  // Reattach to an already-running (or finished) run without starting a new one.
  // The server replays this run's events over SSE, so the log repopulates.
  resume(runId) {
    get().reset()
    set({ runId, status: 'running', percent: 0 })
    get().attach(runId)
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
      onError: (data) =>
        data.stage === 'cancelled'
          ? set({ status: 'cancelled' })
          : set({ status: 'failed', errorMessage: data.message }),
    })
    set({ runId, status: 'running', eventSource: source })
  },

  async cancel() {
    const { runId } = get()
    if (!runId) return
    set({ status: 'cancelling' })
    // The stream's cancelled event flips status to 'cancelled' when the
    // pipeline actually stops (it only checks the flag between stages)
    await cancelRun(runId).catch(() => {})
  },
}))
