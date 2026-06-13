import { useEffect } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { downloadUrl } from '../api'
import { usePipelineStore } from '../store/pipelineStore'

const STAGES = [
  { key: 'extraction', label: 'Extraction' },
  { key: 'analysis', label: 'Analysis' },
  { key: 'generation', label: 'Generation' },
  { key: 'rendering', label: 'Rendering' },
]

const STAGE_ORDER = ['extraction', 'analysis', 'generation', 'rendering', 'done']

export default function Generate() {
  const { id } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const { runId, status, percent, stage, startedAt, messages, errorMessage, start, resume, reset, cancel } = usePipelineStore()

  const startRun = () =>
    start(id).catch((e) => usePipelineStore.setState({ status: 'failed', errorMessage: e.message }))

  useEffect(() => {
    // A run is already attached in this session (e.g. navigated back) — keep its stream.
    if (status !== 'idle') return

    // Reconnect to a running/finished run when arriving from the project page.
    const resumeId = searchParams.get('run')
    if (resumeId) {
      resume(resumeId)
      return
    }
    // Only start a brand-new run on explicit intent (the Generate button adds ?start).
    // A bare reload lands on the idle panel instead of silently launching a second run.
    if (searchParams.get('start')) {
      startRun()
      setSearchParams({}, { replace: true })
    }
  }, [])

  const stageIndex = STAGE_ORDER.indexOf(status === 'done' ? 'done' : stage)

  function stageState(key) {
    const i = STAGE_ORDER.indexOf(key)
    if (status === 'done' || i < stageIndex) return 'done'
    if (i === stageIndex && status === 'running') return 'active'
    return 'pending'
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link to={`/projects/${id}`} className="text-sm text-slate-500 hover:text-slate-900">← Back to project</Link>
      <h1 className="mt-1 text-xl font-semibold">Generating BRD</h1>
      {startedAt && (
        <p className="mb-6 text-sm text-slate-500">Run started {new Date(startedAt).toLocaleString()}</p>
      )}
      {!startedAt && <div className="mb-6" />}

      {/* Progress bar */}
      <div className="mb-6 h-3 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full rounded-full transition-all duration-500 ${status === 'failed' ? 'bg-red-500' : 'bg-blue-600'}`}
          style={{ width: `${status === 'failed' ? 100 : percent}%` }}
        />
      </div>

      {/* Stage checklist */}
      <ol className="mb-6 flex justify-between">
        {STAGES.map((s) => {
          const state = stageState(s.key)
          return (
            <li key={s.key} className="flex items-center gap-2 text-sm">
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                  state === 'done' ? 'bg-green-500 text-white' :
                  state === 'active' ? 'bg-blue-600 text-white' :
                  'bg-slate-200 text-slate-500'
                }`}
              >
                {state === 'done' ? '✓' : ''}
              </span>
              <span className={state === 'pending' ? 'text-slate-400' : ''}>{s.label}</span>
            </li>
          )
        })}
      </ol>

      {/* Live message log (last 5) */}
      {(status === 'running' || status === 'cancelling') && (
        <div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 font-mono text-xs text-slate-600">
            {messages.length === 0 ? 'Starting pipeline…' : messages.map((m, i) => <div key={i}>{m}</div>)}
          </div>
          <div className="mt-4 text-center">
            <button
              onClick={cancel}
              disabled={status === 'cancelling'}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-40"
            >
              {status === 'cancelling' ? 'Cancelling…' : 'Cancel'}
            </button>
          </div>
        </div>
      )}

      {status === 'idle' && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-center">
          <p className="mb-4 text-sm text-slate-600">
            No generation is running. If you started one earlier, return to the project to view its progress.
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={startRun}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Start generation
            </button>
            <Link
              to={`/projects/${id}`}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              Back to project
            </Link>
          </div>
        </div>
      )}

      {status === 'done' && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-6 text-center">
          <p className="mb-4 font-medium text-green-800">Your draft BRD is ready.</p>
          <a
            href={downloadUrl(runId)}
            className="inline-block rounded-md bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Download BRD
          </a>
          <div className="mt-3">
            <Link to={`/projects/${id}`} onClick={reset} className="text-sm text-slate-500 hover:underline">
              Return to project
            </Link>
          </div>
        </div>
      )}

      {status === 'cancelled' && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-center">
          <p className="mb-4 text-sm text-amber-800">Generation cancelled.</p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => { reset(); start(id).catch((e) => usePipelineStore.setState({ status: 'failed', errorMessage: e.message })) }}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Retry
            </button>
            <Link
              to={`/projects/${id}`}
              onClick={reset}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              Return to project
            </Link>
          </div>
        </div>
      )}

      {status === 'failed' && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="mb-4 text-sm text-red-700">{errorMessage || 'Generation failed.'}</p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => { reset(); start(id).catch((e) => usePipelineStore.setState({ status: 'failed', errorMessage: e.message })) }}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Retry
            </button>
            <Link
              to={`/projects/${id}`}
              onClick={reset}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              Return to project
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
