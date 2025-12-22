<template>
  <div>
    <!-- 服务器选择 -->
    <div class="card mb-3">
      <div class="card-header">
        <h3 class="card-title">服务器选择</h3>
      </div>
      <div class="card-body">
        <div class="row g-3 align-items-center">
          <div class="col-auto">
            <label class="form-label">当前服务器：</label>
          </div>
          <div class="col-auto">
            <select class="form-select" v-model="currentServerId" @change="handleServerChange" :disabled="serversStore.loading">
              <option :value="null">请选择服务器...</option>
              <option v-for="server in serversStore.servers" :key="server.id" :value="server.id">
                {{ server.name }}
              </option>
            </select>
          </div>
          <div class="col-auto">
            <button class="btn btn-outline-secondary" @click="testCurrentServer" :disabled="!currentServerId">
              测试连接
            </button>
          </div>
        </div>
      </div>
    </div>

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

const router = useRouter()
const serversStore = useServersStore()
const proxiesStore = useProxiesStore()

const currentServerId = ref(null)
const showConfigDialog = ref(false)
const configGroupName = ref('')

onMounted(async () => {
  try {
    await serversStore.loadServers()
    if (serversStore.servers.length > 0) {
      currentServerId.value = serversStore.currentServerId || serversStore.servers[0].id
    }
  } catch (error) {
    console.error('Load servers error:', error)
  }
})

watch(currentServerId, async (newId) => {
  if (newId) {
    serversStore.setCurrentServer(newId)
  }
})

const handleServerChange = () => {
  // 服务器变化时，GroupManage 组件会自动重新加载
}

const testCurrentServer = async () => {
  if (!currentServerId.value) return
  
  try {
    await serversStore.testServer(currentServerId.value)
    alert('连接测试成功')
    await serversStore.loadServers()
  } catch (error) {
    alert('连接测试失败: ' + error.message)
  }
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

