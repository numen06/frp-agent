import { defineStore } from 'pinia'
import { groupApi } from '@/api/groups'

export const useGroupsStore = defineStore('groups', {
  state: () => ({
    groups: [],
    loading: false
  }),
  
  actions: {
    // 加载分组列表
    async loadGroups(frpsServerId) {
      this.loading = true
      try {
        const response = await groupApi.getGroups({ frps_server_id: frpsServerId })
        this.groups = response.groups || []
      } catch (error) {
        console.error('加载分组列表失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // 创建分组
    async createGroup(data) {
      const group = await groupApi.createGroup(data)
      this.groups.push(group)
      return group
    },
    
    // 更新分组（重命名）
    async updateGroup(oldName, newName, frpsServerId) {
      await groupApi.updateGroup(oldName, newName, { frps_server_id: frpsServerId })
      const group = this.groups.find(g => g.group_name === oldName)
      if (group) {
        group.group_name = newName
      }
    },
    
    // 删除分组
    async deleteGroup(groupName, reassignGroup, frpsServerId) {
      await groupApi.deleteGroup(groupName, reassignGroup)
      this.groups = this.groups.filter(g => g.group_name !== groupName)
      // 重新加载分组列表以更新统计
      await this.loadGroups(frpsServerId)
    },
    
    // 自动分析分组
    async autoAnalyzeGroups(frpsServerId) {
      return await groupApi.autoAnalyzeGroups(frpsServerId)
    }
  }
})

