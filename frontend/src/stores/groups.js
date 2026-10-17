import { defineStore } from 'pinia'
import { groupApi } from '@/api/groups'

export const useGroupsStore = defineStore('groups', {
  state: () => ({
    groups: [],
    loading: false,
    pagination: {
      page: 1,
      page_size: 10,
      total: 0
    },
    filters: {
      search: ''
    },
    _loadRequestId: 0
  }),
  
  actions: {
    // 加载分组列表（仅最后一次请求的结果会写入 state）
    async loadGroups(frpsServerId, params = {}) {
      const requestId = ++this._loadRequestId
      this.loading = true
      try {
        const page = params.page || this.pagination.page
        const page_size = params.page_size || this.pagination.page_size

        const response = await groupApi.getGroups({
          frps_server_id: frpsServerId,
          page,
          page_size,
          search: params.search || this.filters.search || undefined,
          ...params
        })

        if (requestId !== this._loadRequestId) {
          return
        }

        if (response.items !== undefined) {
          this.groups = response.items || []
          this.pagination = {
            page: response.page || page,
            page_size: response.page_size || page_size,
            total: response.total || 0
          }
        } else {
          this.groups = response.groups || []
          this.pagination = {
            page: 1,
            page_size: this.groups.length,
            total: this.groups.length
          }
        }
      } catch (error) {
        if (requestId === this._loadRequestId) {
          console.error('加载分组列表失败:', error)
          throw error
        }
      } finally {
        if (requestId === this._loadRequestId) {
          this.loading = false
        }
      }
    },
    
    // 设置分页
    setPagination(pagination) {
      this.pagination = { ...this.pagination, ...pagination }
    },
    
    // 设置过滤器
    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
    },
    
    // 创建分组
    async createGroup(data) {
      const result = await groupApi.createGroup(data)
      return result
    },
    
    // 更新分组（重命名）
    async updateGroup(oldName, newName, frpsServerId) {
      await groupApi.updateGroup(oldName, newName, { frps_server_id: frpsServerId })
    },

    // 删除分组
    async deleteGroup(groupName, reassignGroup, frpsServerId) {
      const serverId = Number(frpsServerId)
      if (!serverId || isNaN(serverId)) {
        throw new Error('服务器ID无效')
      }
      await groupApi.deleteGroup(groupName, serverId, reassignGroup)
    },
    
    // 自动分析分组
    async autoAnalyzeGroups(frpsServerId) {
      return await groupApi.autoAnalyzeGroups(frpsServerId)
    },

    // 从配置内容导入分组和代理
    async importConfig(data) {
      return await groupApi.importConfig(data)
    }
  }
})

