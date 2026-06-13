const STYLES = {
  EXTRACTING: 'bg-amber-100 text-amber-800',
  TRANSCRIBING: 'bg-amber-100 text-amber-800',
  EXTRACTED: 'bg-green-100 text-green-800',
  PENDING: 'bg-slate-200 text-slate-600',
  ERROR: 'bg-red-100 text-red-800',
  UPLOADED: 'bg-slate-200 text-slate-600',
}

const LABELS = {
  EXTRACTING: 'Extracting…',
  TRANSCRIBING: 'Transcribing…',
  EXTRACTED: 'Ready',
  PENDING: 'Pending',
  ERROR: 'Error',
  UPLOADED: 'Uploaded',
}

// All media share the TRANSCRIBING status, but only audio/video are transcribed —
// images are read by the AI vision model, so they get their own wording.
function labelFor(status, filetype) {
  if (status === 'TRANSCRIBING' && filetype === 'image') return 'Reading image…'
  return LABELS[status] || status
}

function defaultTitle(status, filetype) {
  if (status === 'PENDING') return 'Uploaded before media processing existed — press Process'
  if (status === 'TRANSCRIBING' && filetype === 'image') return 'Sent to your AI provider to read the image'
  return undefined
}

export default function StatusBadge({ status, filetype, title }) {
  return (
    <span
      title={title || defaultTitle(status, filetype)}
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status] || STYLES.UPLOADED}`}
    >
      {labelFor(status, filetype)}
    </span>
  )
}
