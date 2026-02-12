import { defineStore } from 'pinia'
import { proxyApi } from '@/api/proxies'

export const useProxiesStore = defineStore('proxies', {
  state: () => ({
    proxies: [],
    allProxies: [], // 保存所有代理用于过滤
    filters: {
      group: '',
      status: '',
      search: '' // 搜索关键词
    },
    selectedProxyIds: new Set(),
    loading: false,
    pagination: {
      page: 1,
      page_size: 10,
      total: 0
    },
    stats: {
      total: 0,
      online: 0,
      offline: 0,
      portCount: 0
    }
  }),
  
  getters: {
    filteredProxies: (state) => {
      // 由于使用后端分页和搜索，前端不需要再过滤
      return state.proxies
    },
    
    selectedCount: (state) => state.selectedProxyIds.size
  },
  
  actions: {
    // 加载代理列表
    async loadProxies(frpsServerId, params = {}) {
      this.loading = true
      try {
        const page = params.page || this.pagination.page
        const page_size = params.page_size || this.pagination.page_size
        
        const response = await proxyApi.getProxies({
          frps_server_id: frpsServerId,
          sync_from_frps: params.syncFromFrps === true,
          page,
          page_size,
          group_name: params.group_name || this.filters.group || undefined,
          status_filter: params.status_filter || this.filters.status || undefined,
          search: params.search || this.filters.search || undefined,
          ...params
        })
        
        // 处理分页响应格式
        if (response.items !== undefined) {
          // 新的分页格式，按 id 去重（防止后端返回重复）
          const items = response.items || []
          const seen = new Set()
          this.proxies = items.filter(p => {
            if (seen.has(p.id)) return false
            seen.add(p.id)
            return true
          })
          this.pagination = {
            page: response.page || page,
            page_size: response.page_size || page_size,
            total: response.total || 0
          }
        } else {
          // 兼容旧格式（无分页），按 id 去重
          const items = response.proxies || []
          const seen = new Set()
          this.proxies = items.filter(p => {
            if (seen.has(p.id)) return false
            seen.add(p.id)
            return true
          })
          this.pagination = {
            page: 1,
            page_size: this.proxies.length,
            total: this.proxies.length
          }
        }
        
        this.allProxies = [...this.proxies]
        
        // 更新统计信息
        this.updateStats()
      } catch (error) {
        console.error('加载代理列表失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // 设置分页
    setPagination(pagination) {
      this.pagination = { ...this.pagination, ...pagination }
    },
    
    // 更新统计信息
    updateStats() {
      this.stats.total = this.proxies.length
      this.stats.online = this.proxies.filter(p => p.status === 'online').length
      this.stats.offline = this.proxies.filter(p => p.status === 'offline').length
      
      // 计算端口数量（去重）
      const ports = new Set()
      this.proxies.forEach(p => {
        if (p.remote_port) ports.add(p.remote_port)
      })
      this.stats.portCount = ports.size
    },
    
    // 设置过滤器
    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
    },
    
    // 切换代理选中状态
    toggleProxySelection(id) {
      if (this.selectedProxyIds.has(id)) {
        this.selectedProxyIds.delete(id)
      } else {
        this.selectedProxyIds.add(id)
      }
    },
    
    // 全选/取消全选
    toggleSelectAll(ids) {
      if (this.selectedProxyIds.size === ids.length) {
        this.selectedProxyIds.clear()
      } else {
        this.selectedProxyIds = new Set(ids)
      }
    },
    
    // 清空选择
    clearSelection() {
      this.selectedProxyIds.clear()
    },
    
    // 添加代理
    async addProxy(data) {
      const proxy = await proxyApi.createProxy(data)
      this.proxies.push(proxy)
      this.updateStats()
      return proxy
    },
    
    // 更新代理
    async updateProxy(id, data) {
      const proxy = await proxyApi.updateProxy(id, data)
      const index = this.proxies.findIndex(p => p.id === id)
      if (index !== -1) {
        this.proxies[index] = proxy
      }
      this.updateStats()
      return proxy
    },
    
    // 删除代理
    async deleteProxy(id) {
      await proxyApi.deleteProxy(id)
      this.proxies = this.proxies.filter(p => p.id !== id)
      this.selectedProxyIds.delete(id)
      this.updateStats()
    },
    
    // 批量识别端口
    async batchDetectPorts(proxyIds) {
      return await proxyApi.batchDetectPorts(proxyIds)
    },
    
    // 批量更新分组
    async bulkUpdateGroup(proxyIds, groupName) {
      await proxyApi.bulkUpdateGroup(proxyIds, groupName)
      // 更新本地状态
      this.proxies.forEach(p => {
        if (proxyIds.includes(p.id)) {
          p.group_name = groupName
        }
      })
    }
  }
})

