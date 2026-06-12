import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useProjectStore } from '../store/projectStore'
import { useSettingsStore } from '../store/settingsStore'

const VERSIONS = [
  { key: 'maximo-76', label: 'Maximo 7.6.x' },
  { key: 'mas-8', label: 'MAS 8.x' },
  { key: 'mas-9', label: 'MAS 9.x' },
]

// Projects created before the 7.6 entries were merged may still use these keys.
const LEGACY_VERSION_LABELS = { 'maximo-760': 'Maximo 7.6.x', 'maximo-761': 'Maximo 7.6.x' }

function NewProjectModal({ onClose }) {
  const navigate = useNavigate()
  const createProject = useProjectStore((s) => s.createProject)
  const [clientName, setClientName] = useState('')
  const [projectName, setProjectName] = useState('')
  const [projectDate, setProjectDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [version, setVersion] = useState('mas-9')
  const [folderPath, setFolderPath] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const valid = clientName.trim() && projectName.trim() && projectDate

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      const project = await createProject({
        client_name: clientName.trim(),
        project_name: projectName.trim(),
        project_date: projectDate,
        maximo_version: version,
        folder_path: folderPath.trim() || null,
      })
      navigate(`/projects/${project.id}`)
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  const field = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none'

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">New Project</h2>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Client name *</label>
            <input className={field} value={clientName} onChange={(e) => setClientName(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Project name *</label>
            <input className={field} value={projectName} onChange={(e) => setProjectName(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Project date *</label>
            <input type="date" className={field} value={projectDate} onChange={(e) => setProjectDate(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Maximo version *</label>
            <select className={field} value={version} onChange={(e) => setVersion(e.target.value)}>
              {VERSIONS.map((v) => (
                <option key={v.key} value={v.key} disabled={v.disabled}>{v.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Project folder</label>
            <input
              className={field}
              placeholder="Leave blank for ~/MaximoBRD/client-project"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
            />
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={!valid || busy}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {busy ? 'Creating…' : 'Create Project'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ProjectList() {
  const { projects, loadProjects, deleteProject } = useProjectStore()
  const { configured, loaded, load } = useSettingsStore()
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    loadProjects()
    if (!loaded) load()
  }, [])

  return (
    <div>
      {loaded && !configured && (
        <div className="mb-6 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          No AI provider configured yet —{' '}
          <Link to="/settings" className="font-medium underline">open Settings</Link> to add your API key.
        </div>
      )}

      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Projects</h1>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
          Create your first project
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Maximo</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3">{p.client_name}</td>
                  <td className="px-4 py-3">
                    <Link to={`/projects/${p.id}`} className="font-medium text-blue-600 hover:underline">
                      {p.project_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{p.project_date}</td>
                  <td className="px-4 py-3">{VERSIONS.find((v) => v.key === p.maximo_version)?.label || LEGACY_VERSION_LABELS[p.maximo_version] || p.maximo_version}</td>
                  <td className="px-4 py-3 text-slate-500">{new Date(p.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => { if (confirm(`Remove "${p.project_name}" from the list? Files stay on disk.`)) deleteProject(p.id) }}
                      className="text-xs text-slate-400 hover:text-red-600"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && <NewProjectModal onClose={() => setShowModal(false)} />}
    </div>
  )
}
