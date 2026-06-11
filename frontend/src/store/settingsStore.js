import { create } from 'zustand'
import { apiGet, apiPost } from '../api'

export const useSettingsStore = create((set) => ({
  provider: 'anthropic',
  modelId: 'claude-sonnet-4-6',
  configured: false,
  providers: [], // [{ key, label, default_model, models_url, configured }]
  loaded: false,

  async load() {
    const data = await apiGet('/settings/provider')
    set({
      provider: data.provider,
      modelId: data.model_id,
      configured: data.configured,
      providers: data.providers,
      loaded: true,
    })
  },

  async save(provider, modelId, apiKey) {
    if (apiKey) {
      await apiPost('/settings/api-key', { provider, api_key: apiKey })
    }
    const data = await apiPost('/settings/provider', { provider, model_id: modelId })
    set({
      provider: data.provider,
      modelId: data.model_id,
      configured: data.configured,
      providers: data.providers,
    })
  },

  async testConnection(provider, modelId, apiKey) {
    // Tests exactly what the form shows — an unsaved key is tested without being stored
    return apiPost('/settings/provider/test', {
      provider,
      model_id: modelId || null,
      api_key: apiKey || null,
    })
  },
}))
