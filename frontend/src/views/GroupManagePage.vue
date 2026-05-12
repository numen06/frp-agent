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
      @generate-config="handleGenerateGroupConfig"
    />
    <div v-else class="overflow-hidden rounded-xl border border-gray-200 bg-white p-10 text-center text-sm text-gray-500 shadow-sm">
      请先选择服务器
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
import { ref, onMounted } from 'vue'
import { useServersStore } from '@/stores/servers'
import GroupManage from '@/components/GroupManage.vue'
import ConfigGenerateDialog from '@/components/ConfigGenerateDialog.vue'
import ServerSelector from '@/components/ServerSelector.vue'

const serversStore = useServersStore()

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

const handleServerChange = () => {
  // 服务器变化时，GroupManage 组件会自动重新加载
}

const handleTestServer = async () => {
  alert('连接测试成功')
  serversStore.markRefreshNeeded()
  await serversStore.loadServers()
}

const handleGenerateGroupConfig = (groupName) => {
  configGroupName.value = groupName
  showConfigDialog.value = true
}
</script>

