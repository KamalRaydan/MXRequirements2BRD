import { useEffect, useState } from 'react'
import { useSettingsStore } from '../store/settingsStore'

export default function Settings() {
  const { modelId, configured, loaded, load, save, testConnection } = useSettingsStore()
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [message, setMessage] = useState(null) // { kind: 'ok' | 'err', text }
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!loaded) load()
  }, [])

  useEffect(() => {
    if (loaded) setModel(modelId)
  }, [loaded, modelId])

  async function handleSave() {
    setBusy(true)
    setMessage(null)
    try {
      await save(model.trim() || 'claude-sonnet-4-6', apiKey.trim() || null)
      setApiKey('')
      setMessage({ kind: 'ok', text: 'Settings saved. Your key is stored in the macOS Keychain.' })
    } catch (e) {
      setMessage({ kind: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  async function handleTest() {
    setBusy(true)
    setMessage(null)
    try {
      const result = await testConnection()
      setMessage({ kind: 'ok', text: `Connection OK (${result.latency_ms} ms)` })
    } catch (e) {
      setMessage({ kind: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const field = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none'

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-6 text-xl font-semibold">Settings</h1>

      <div className="space-y-5 rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <label className="mb-1 block text-sm font-medium">AI Provider</label>
          <div className="flex items-center gap-2 text-sm">
            <input type="radio" checked readOnly id="prov-claude" />
            <label htmlFor="prov-claude">Anthropic Claude</label>
            <span className="ml-2 text-xs text-slate-400">(more providers in a later release)</span>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Model</label>
          <input
            className={field}
            placeholder="claude-sonnet-4-6"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">API key</label>
          <input
            type="password"
            className={field}
            placeholder={configured ? '••••••••••••  (saved in Keychain — enter to replace)' : 'sk-ant-…'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <p className="mt-1 text-xs text-slate-400">
            Stored only in the macOS Keychain — never in files, the database, or logs.
          </p>
        </div>

        {message && (
          <p className={`text-sm ${message.kind === 'ok' ? 'text-green-700' : 'text-red-600'}`}>
            {message.text}
          </p>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={busy}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            Save
          </button>
          <button
            onClick={handleTest}
            disabled={busy || (!configured && !apiKey)}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-40"
          >
            Test Connection
          </button>
        </div>
      </div>
    </div>
  )
}
