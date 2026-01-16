<template>
  <div>
    <!-- 服务器选择 -->
    <ServerSelector 
      v-model="currentServerId" 
      @change="handleServerChange"
      @test="handleTestServer"
    />

    <!-- 分组管理 -->
    <GroupManage
      v-if="currentServerId"
      :server-id="currentServerId"
      :highlight-group="highlightGroupName"
      @view-group="handleViewGroup"
      @generate-config="handleGenerateGroupConfig"
    />
    <div v-else class="card">
      <div class="card-body text-center text-muted py-5">
        请先选择服务器
      </div>
    </div>


    <!-- 生成配置对话框 -->
    <ConfigGenerateDialog
      v-model="showConfigDialog"
      :server-id="currentServerId"
      :group-name="configGroupName"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useServersStore } from '@/stores/servers'
import { useProxiesStore } from '@/stores/proxies'
import GroupManage from '@/components/GroupManage.vue'
import ConfigGenerateDialog from '@/components/ConfigGenerateDialog.vue'
import ServerSelector from '@/components/ServerSelector.vue'

const router = useRouter()
const route = useRoute()
const serversStore = useServersStore()
const proxiesStore = useProxiesStore()

const currentServerId = ref(null)
const showConfigDialog = ref(false)
const configGroupName = ref('')
const highlightGroupName = ref('')

onMounted(async () => {
  // ServerSelector 组件会自动加载服务器列表并设置默认值
  // 这里只需要等待服务器列表加载完成
  try {
    if (serversStore.servers.length === 0) {
      await serversStore.loadServers()
    }
    
    // 如果 URL 中有 server_id 参数，设置当前服务器
    const serverIdFromQuery = route.query.server_id
    if (serverIdFromQuery) {
      const serverId = parseInt(serverIdFromQuery)
      if (!isNaN(serverId)) {
        currentServerId.value = serverId
      }
    }
  } catch (error) {
    console.error('Load servers error:', error)
  }
})

watch(currentServerId, async (newId) => {
  // ServerSelector 组件内部已经调用了 setCurrentServer
  // 这里不需要重复调用
  
  // 如果 URL 中有 group 参数，设置要高亮的分组
  if (newId && route.query.group) {
    highlightGroupName.value = route.query.group
    // 不清除 group 查询参数，保留在URL中以便刷新时仍然有效
  }
})

// 监听路由查询参数变化
watch(() => route.query, (newQuery) => {
  // 如果 URL 中有 server_id 参数，设置当前服务器
  if (newQuery.server_id) {
    const serverId = parseInt(newQuery.server_id)
    if (!isNaN(serverId) && serverId !== currentServerId.value) {
      currentServerId.value = serverId
    }
  }
  
  // 如果 URL 中有 group 参数，设置要高亮的分组
  if (newQuery.group && currentServerId.value) {
    highlightGroupName.value = newQuery.group
  }
}, { immediate: true })

const handleServerChange = () => {
  // 服务器变化时，GroupManage 组件会自动重新加载
}

const handleTestServer = async () => {
  alert('连接测试成功')
  await serversStore.loadServers()
}

const handleViewGroup = (groupName) => {
  router.push({
    path: '/proxies',
    query: { group: groupName }
  })
}

const handleGenerateGroupConfig = (groupName) => {
  configGroupName.value = groupName
  showConfigDialog.value = true
}
</script>

