import { defineStore } from 'pinia'
import { serverApi } from '@/api/servers'

export const useServersStore = defineStore('servers', {
  state: () => ({
    servers: [],
    currentServerId: null,
    loading: false,
    _needsRefresh: false
  }),
  
  getters: {
    currentServer: (state) => {
      return state.servers.find(s => s.id === state.currentServerId) || null
    }
  },
  
  actions: {
    // 加载服务器列表
    async loadServers() {
      // 如果已有数据且未标记为需要刷新，直接返回
      if (this.servers.length > 0 && !this._needsRefresh) {
        return
      }
      this.loading = true
      try {
        this.servers = await serverApi.getServers()
        this._needsRefresh = false
        // 恢复之前选中的服务器
        const savedServerId = localStorage.getItem('currentServerId')
        if (savedServerId && this.servers.find(s => s.id === parseInt(savedServerId))) {
          this.currentServerId = parseInt(savedServerId)
        } else if (this.servers.length > 0) {
          this.currentServerId = this.servers[0].id
        }
      } catch (error) {
        console.error('加载服务器列表失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // 标记需要刷新服务器列表（在增删改后调用）
    markRefreshNeeded() {
      this._needsRefresh = true
    },
    
    // 设置当前服务器
    setCurrentServer(id) {
      this.currentServerId = id
      localStorage.setItem('currentServerId', id)
    },
    
    // 添加服务器
    async addServer(data) {
      const server = await serverApi.createServer(data)
      this.servers.push(server)
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



