import { useEffect, useState } from 'react'
import { useSettingsStore } from '../store/settingsStore'

export default function Settings() {
  const { provider, modelId, providers, loaded, load, save, testConnection } = useSettingsStore()
  const [selectedProvider, setSelectedProvider] = useState('anthropic')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [message, setMessage] = useState(null) // { kind: 'ok' | 'err', text }
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!loaded) load()
  }, [])

  // When settings arrive, mirror the saved provider + model into the form
  useEffect(() => {
    if (loaded) {
      setSelectedProvider(provider)
      setModel(modelId)
    }
  }, [loaded, provider, modelId])

  const info = providers.find((p) => p.key === selectedProvider)

  function pickProvider(key) {
    setSelectedProvider(key)
    setApiKey('')
    setMessage(null)
    const next = providers.find((p) => p.key === key)
    // Saved model for the saved provider; suggested default for the other one
    setModel(key === provider ? modelId : next?.default_model || '')
  }

  async function handleSave() {
    setBusy(true)
    setMessage(null)
    try {
      await save(selectedProvider, model.trim() || info?.default_model || '', apiKey.trim() || null)
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
      const result = await testConnection(selectedProvider, model.trim(), apiKey.trim())
      setMessage({ kind: 'ok', text: `Connection OK (${result.latency_ms} ms)` })
    } catch (e) {
      setMessage({ kind: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const field = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none'
  const keyPlaceholder = selectedProvider === 'openai' ? 'sk-…' : 'sk-ant-…'

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-6 text-xl font-semibold">Settings</h1>

      <div className="space-y-5 rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <label className="mb-2 block text-sm font-medium">AI Provider</label>
          <div className="space-y-2">
            {providers.map((p) => (
              <div key={p.key} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  id={`prov-${p.key}`}
                  checked={selectedProvider === p.key}
                  onChange={() => pickProvider(p.key)}
                />
                <label htmlFor={`prov-${p.key}`}>{p.label}</label>
                {p.configured && (
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">
                    key saved
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Model</label>
          <input
            className={field}
            placeholder={info?.default_model || ''}
            value={model}
            onChange={(e) => setModel(e.target.value)}
          />
          {info && (
            <p className="mt-1 text-xs text-slate-400">
              Type any {info.label} model name —{' '}
              <a
                href={info.models_url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 underline"
              >
                view available models ↗
              </a>
            </p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">API key</label>
          <input
            type="password"
            className={field}
            placeholder={info?.configured ? '••••••••••••  (saved in Keychain — enter to replace)' : keyPlaceholder}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <p className="mt-1 text-xs text-slate-400">
            Stored only in the macOS Keychain — never in files, the database, or logs. Each provider keeps its own key.
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
            disabled={busy || (!info?.configured && !apiKey)}
            title={!info?.configured && !apiKey ? 'Enter or save a key first' : undefined}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-40"
          >
            Test Connection
          </button>
        </div>
        <p className="text-xs text-slate-400">
          Test Connection uses the provider, model, and key shown above — an unsaved key is tested without being stored.
        </p>
      </div>
    </div>
  )
}
