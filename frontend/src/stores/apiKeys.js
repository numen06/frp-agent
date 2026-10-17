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
    pagination: { page: 1, page_size: 20, total: 0 },
    search: '',
    selectedRecord: null,
    _request: 0,
    selectedKeyId: null,
    error: '',
    loading: false
  }),

  getters: {
    availableKeys: state => [...state.keys, ...(state.selectedRecord && !state.keys.some(key => key.id === state.selectedRecord.id) ? [state.selectedRecord] : [])].filter(key => key.is_active && !key.is_expired),
    selectedKey(state) {
      if (!state.selectedKeyId) return null
      return (state.keys || []).find((k) => k.id === state.selectedKeyId) || state.selectedRecord
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

    async ensureSelectedKey() {
      const request = this._request
      const selectedId = this.selectedKeyId
      const isCurrent = () => request === this._request && selectedId === this.selectedKeyId
      if (selectedId) {
        try {
          const item = await apiKeysApi.get(selectedId)
          if (!isCurrent()) return
          if (item.is_active && !item.is_expired) { this.selectedRecord = item; return }
        } catch { if (!isCurrent()) return }
      }
      const data = await apiKeysApi.list({ page: 1, page_size: 1, available_only: true })
      if (!isCurrent()) return
      this.selectedRecord = data.items[0] || null
      this.setDefaultKey(this.selectedRecord?.id)
    },

    async loadKeys(page = this.pagination.page) {
      const request = ++this._request
      this.error = ''
      this.loading = true
      try {
        const data = await apiKeysApi.list({ page, page_size: this.pagination.page_size, search: this.search || undefined })
        if (request !== this._request) return
        const lastPage = Math.max(1, Math.ceil(data.total / this.pagination.page_size))
        if (page > lastPage) return await this.loadKeys(lastPage)
        this.keys = data.items
        Object.assign(this.pagination, { page: data.page, page_size: data.page_size, total: data.total })
        await this.ensureSelectedKey()
      } catch (error) { if (request === this._request) this.error = error.message || '加载失败，请重试' }
      finally { if (request === this._request) this.loading = false }
    },
    async resize(size) { this.pagination.page_size = size; await this.loadKeys(1) },

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
