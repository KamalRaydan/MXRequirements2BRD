import { useEffect, useState } from 'react'
import { getSourceText } from '../api'

// What the extracted text actually represents, by file type. Images go to an AI
// vision model; audio/video are transcribed locally; everything else is read
// straight from the file. The note tells the user how much to trust it.
function describeSource(filetype) {
  if (filetype === 'image') {
    return {
      heading: 'What the AI read from this image',
      note:
        'This image was sent to your AI provider, which described it in words. ' +
        'The text below — not the image — is what gets used to build your BRD.',
    }
  }
  if (filetype === 'audio' || filetype === 'video') {
    return {
      heading: 'Transcript',
      note: 'This file was transcribed to text on your machine. The transcript below is what gets used to build your BRD.',
    }
  }
  return {
    heading: 'Extracted text',
    note: 'This is the text pulled from the file that gets used to build your BRD.',
  }
}

export default function SourceTextModal({ projectId, source, onClose }) {
  const [state, setState] = useState({ loading: true, error: null, text: '', charCount: 0 })

  // Fetch the text when the modal opens; the `active` flag avoids setting state
  // after the user has already closed it.
  useEffect(() => {
    let active = true
    getSourceText(projectId, source.id)
      .then((d) => active && setState({ loading: false, error: null, text: d.text, charCount: d.char_count }))
      .catch((e) => active && setState({ loading: false, error: e.message, text: '', charCount: 0 }))
    return () => {
      active = false
    }
  }, [projectId, source.id])

  // Close on Escape, like a standard dialog
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const { heading, note } = describeSource(source.filetype)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">{heading}</h2>
            <p className="mt-0.5 text-xs text-slate-500">{source.filename}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700" aria-label="Close">
            ✕
          </button>
        </div>

        <div className="border-b border-slate-100 bg-slate-50 px-5 py-3 text-xs text-slate-600">{note}</div>

        <div className="flex-1 overflow-auto px-5 py-4">
          {state.loading && <p className="text-sm text-slate-400">Loading…</p>}
          {state.error && <p className="text-sm text-red-600">{state.error}</p>}
          {!state.loading && !state.error && (
            <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-800">
              {state.text}
            </pre>
          )}
        </div>

        {!state.loading && !state.error && (
          <div className="border-t border-slate-100 px-5 py-3 text-right text-xs text-slate-400">
            {state.charCount.toLocaleString()} characters
          </div>
        )}
      </div>
    </div>
  )
}
