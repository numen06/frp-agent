import { defineStore } from 'pinia'
import { apiKeysApi } from '@/api/apiKeys'

const DEFAULT_KEY_STORAGE = 'default_api_key_id'

const isValidFullKey = (value, id) => {
  if (!value) return false
  const text = String(value).trim()
  if (!text) return false
  if (text === String(id) || text === String(Number(id))) return false
  return text.length > 20
}

export const useApiKeysStore = defineStore('apiKeys', {
  state: () => ({
    keys: [],
    selectedKeyId: null,
    loading: false
  }),

  getters: {
    availableKeys: (state) => (state.keys || []).filter((k) => k.is_active && !k.is_expired),
    selectedKey(state) {
      if (!state.selectedKeyId) return null
      return (state.keys || []).find((k) => k.id === state.selectedKeyId) || null
    }
  },

  actions: {
    getStoredDefaultId() {
      const raw = localStorage.getItem(DEFAULT_KEY_STORAGE)
      if (!raw) return null
      const id = Number(raw)
      return Number.isInteger(id) && id > 0 ? id : null
    },

    setDefaultKey(id) {
      const parsed = Number(id)
      if (!Number.isInteger(parsed) || parsed <= 0) {
        this.selectedKeyId = null
        localStorage.removeItem(DEFAULT_KEY_STORAGE)
        return
      }
      this.selectedKeyId = parsed
      localStorage.setItem(DEFAULT_KEY_STORAGE, String(parsed))
    },

    ensureSelectedKey() {
      const current = this.availableKeys.find((k) => k.id === this.selectedKeyId)
      if (current) return
      const fallback = this.availableKeys[0]
      this.setDefaultKey(fallback ? fallback.id : null)
    },

    async loadKeys() {
      this.loading = true
      try {
        const data = await apiKeysApi.list()
        this.keys = Array.isArray(data) ? data : []
        this.ensureSelectedKey()
      } catch (error) {
        console.warn('获取 API Key 列表失败', error)
        this.keys = []
        this.setDefaultKey(null)
      } finally {
        this.loading = false
      }
    },

    async init() {
      this.selectedKeyId = this.getStoredDefaultId()
      await this.loadKeys()
    },

    async resolveFullKey(id) {
      const idNum = Number(id)
      if (!Number.isInteger(idNum) || idNum <= 0) return ''

      const cacheKeys = [
        `api_key_${idNum}`,
        `api_key_${String(idNum)}`
      ]
      for (const cacheKey of cacheKeys) {
        const cached = localStorage.getItem(cacheKey)
        if (isValidFullKey(cached, idNum)) {
          return String(cached).trim()
        }
      }

      try {
        const result = await apiKeysApi.getFullKey(idNum)
        if (result?.key && isValidFullKey(result.key, idNum)) {
          const fullKey = String(result.key).trim()
          localStorage.setItem(`api_key_${idNum}`, fullKey)
          localStorage.setItem(`api_key_${String(idNum)}`, fullKey)
          return fullKey
        }
      } catch (error) {
        console.warn('获取完整 API Key 失败', error)
      }
      return ''
    },

    async resolveDefaultFullKey() {
      if (this.selectedKeyId) {
        const selected = await this.resolveFullKey(this.selectedKeyId)
        if (selected) return selected
      }

      for (const item of this.availableKeys) {
        const fullKey = await this.resolveFullKey(item.id)
        if (fullKey) {
          this.setDefaultKey(item.id)
          return fullKey
        }
      }
      return ''
    }
  }
})
