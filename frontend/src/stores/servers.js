import { defineStore } from 'pinia'
import { serverApi } from '@/api/servers'

export const useServersStore = defineStore('servers', {
  state: () => ({
    servers: [],
    pagination: { page: 1, page_size: 20, total: 0 },
    search: '',
    selectedRecord: null,
    _request: 0,
    currentServerId: null,
    error: '',
    loading: false,
    _needsRefresh: false
  }),
  
  getters: {
    currentServer: (state) => {
      return state.servers.find(s => s.id === state.currentServerId) || state.selectedRecord
    }
  },
  
  actions: {
    // 加载服务器列表
    async loadServers(page = this.pagination.page) {
      const request = ++this._request
      this.error = ''
      this.loading = true
      try {
        const data = await serverApi.getServers({ page, page_size: this.pagination.page_size, search: this.search || undefined })
        if (request !== this._request) return
        const lastPage = Math.max(1, Math.ceil(data.total / this.pagination.page_size))
        if (page > lastPage) return await this.loadServers(lastPage)
        this.servers = data.items
        Object.assign(this.pagination, { page: data.page, page_size: data.page_size, total: data.total })
        this._needsRefresh = false
        const id = this.currentServerId || Number(localStorage.getItem('currentServerId')) || this.servers[0]?.id
        if (id) await this.setCurrentServer(id)
      } catch (error) { if (request === this._request) this.error = error.message || '加载失败，请重试' }
      finally { if (request === this._request) this.loading = false }
    },
    async resize(size) { this.pagination.page_size = size; await this.loadServers(1) },

    // 标记需要刷新服务器列表（在增删改后调用）
    markRefreshNeeded() {
      this._needsRefresh = true
    },
    
    // 设置当前服务器
    async setCurrentServer(id) {
      this.currentServerId = id || null
      const row = this.servers.find(server => server.id === id)
      if (row) this.selectedRecord = row
      else if (id && this.selectedRecord?.id !== id) {
        try { this.selectedRecord = await serverApi.getServer(id) }
        catch (error) {
          if (this.currentServerId === id) {
            this.currentServerId = this.servers[0]?.id || null
            this.selectedRecord = this.servers[0] || null
          }
        }
      }
      if (this.currentServerId) localStorage.setItem('currentServerId', this.currentServerId)
      else localStorage.removeItem('currentServerId')
    },

    // 添加服务器
    async addServer(data) {
      const server = await serverApi.createServer(data)
      await this.loadServers()
      this._needsRefresh = true
      return server
    },
    
    // 更新服务器
    async updateServer(id, data) {
      const server = await serverApi.updateServer(id, data)
      const index = this.servers.findIndex(s => s.id === id)
      if (index !== -1) {
        this.servers[index] = server
      }
      this._needsRefresh = true
      return server
    },
    
    // 删除服务器
    async deleteServer(id) {
      await serverApi.deleteServer(id)
      this.servers = this.servers.filter(s => s.id !== id)
      if (this.currentServerId === id) {
        this.currentServerId = this.servers.length > 0 ? this.servers[0].id : null
      }
      this.selectedRecord = this.currentServerId ? this.selectedRecord : null
      await this.loadServers()
      this._needsRefresh = true
    },
    
    // 测试服务器连接
    async testServer(id) {
      const result = await serverApi.testServer(id)
      // 无论测试成功还是失败，都重新获取服务器详情以更新状态
      // 因为后端已经更新了数据库中的测试状态
      try {
        const updatedServer = await serverApi.getServer(id)
        const index = this.servers.findIndex(s => s.id === id)
        if (index !== -1) {
          this.servers[index] = updatedServer
        }
      } catch (error) {
        // 如果获取服务器详情失败，不影响测试结果的返回
        console.error('更新服务器状态失败:', error)
      }
      return result
    },

    async refreshFrpVersion(id, params = { refresh_proxies: true }) {
      const result = await serverApi.refreshFrpVersion(id, params)
      const updatedServer = await serverApi.getServer(id)
      const index = this.servers.findIndex(s => s.id === id)
      if (index !== -1) {
        this.servers[index] = updatedServer
      }
      return result
    }
  }
})



