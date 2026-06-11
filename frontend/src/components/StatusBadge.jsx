const STYLES = {
  EXTRACTING: 'bg-amber-100 text-amber-800',
  EXTRACTED: 'bg-green-100 text-green-800',
  PENDING: 'bg-slate-200 text-slate-600',
  ERROR: 'bg-red-100 text-red-800',
  UPLOADED: 'bg-slate-200 text-slate-600',
}

const LABELS = {
  EXTRACTING: 'Extracting…',
  EXTRACTED: 'Ready',
  PENDING: 'Pending',
  ERROR: 'Error',
  UPLOADED: 'Uploaded',
}

export default function StatusBadge({ status, title }) {
  return (
    <span
      title={title || (status === 'PENDING' ? 'Media processing arrives in a later release' : undefined)}
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status] || STYLES.UPLOADED}`}
    >
      {LABELS[status] || status}
    </span>
  )
}
