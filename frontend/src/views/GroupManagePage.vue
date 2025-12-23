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
import { useRouter } from 'vue-router'
import { useServersStore } from '@/stores/servers'
import { useProxiesStore } from '@/stores/proxies'
import GroupManage from '@/components/GroupManage.vue'
import ConfigGenerateDialog from '@/components/ConfigGenerateDialog.vue'
import ServerSelector from '@/components/ServerSelector.vue'

const router = useRouter()
const serversStore = useServersStore()
const proxiesStore = useProxiesStore()

const currentServerId = ref(null)
const showConfigDialog = ref(false)
const configGroupName = ref('')

onMounted(async () => {
  // ServerSelector 组件会自动加载服务器列表并设置默认值
  // 这里只需要等待服务器列表加载完成
  try {
    if (serversStore.servers.length === 0) {
      await serversStore.loadServers()
    }
  } catch (error) {
    console.error('Load servers error:', error)
  }
})

watch(currentServerId, async (newId) => {
  // ServerSelector 组件内部已经调用了 setCurrentServer
  // 这里不需要重复调用
})

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

