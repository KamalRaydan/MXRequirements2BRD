import { create } from 'zustand'
import { apiGet, apiPost } from '../api'

export const useSettingsStore = create((set) => ({
  provider: 'anthropic',
  modelId: 'claude-sonnet-4-6',
  configured: false,
  loaded: false,

  async load() {
    const data = await apiGet('/settings/provider')
    set({ provider: data.provider, modelId: data.model_id, configured: data.configured, loaded: true })
  },

  async save(modelId, apiKey) {
    await apiPost('/settings/provider', { provider: 'anthropic', model_id: modelId })
    if (apiKey) {
      await apiPost('/settings/api-key', { api_key: apiKey })
    }
    const data = await apiGet('/settings/provider')
    set({ provider: data.provider, modelId: data.model_id, configured: data.configured })
  },

  async testConnection() {
    return apiPost('/settings/provider/test')
  },
}))
