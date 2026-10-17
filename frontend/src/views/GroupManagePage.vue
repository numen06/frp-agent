<template>
  <div>
    <!-- 服务器选择 -->
    <ServerSelector 
      v-model="currentServerId" 
      @test="handleTestServer"
    />

    <!-- 分组管理 -->
    <GroupManage
      v-if="currentServerId"
      :server-id="currentServerId"
      :highlight-group="highlightGroup"
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useServersStore } from '@/stores/servers'
import GroupManage from '@/components/GroupManage.vue'
import ConfigGenerateDialog from '@/components/ConfigGenerateDialog.vue'
import ServerSelector from '@/components/ServerSelector.vue'

const route = useRoute()
const serversStore = useServersStore()

const currentServerId = ref(null)
const showConfigDialog = ref(false)
const configGroupName = ref('')

const highlightGroup = computed(() => String(route.query.group || ''))

function parseServerIdFromRoute() {
  const raw = route.query.server_id
  if (raw == null || raw === '') return null
  const id = Number(raw)
  return Number.isFinite(id) && id > 0 ? id : null
}

function resolveInitialServerId() {
  const fromQuery = parseServerIdFromRoute()
  if (fromQuery) return fromQuery
  if (serversStore.currentServerId) return serversStore.currentServerId
  if (serversStore.servers.length > 0) return serversStore.servers[0].id
  return null
}

onMounted(async () => {
  try {
    if (serversStore.servers.length === 0) {
      await serversStore.loadServers()
    }
    const id = resolveInitialServerId()
    if (id) {
      currentServerId.value = id
      serversStore.setCurrentServer(id)
    }
  } catch (error) {
    console.error('Load servers error:', error)
  }
})

watch(() => route.query.server_id, () => {
  const id = parseServerIdFromRoute()
  if (id) {
    currentServerId.value = id
    serversStore.setCurrentServer(id)
  }
})

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
