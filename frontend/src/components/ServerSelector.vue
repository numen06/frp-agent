<template>
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
          <select 
            class="form-select" 
            v-model="selectedServerId" 
            @change="handleServerChange" 
            :disabled="serversStore.loading"
          >
            <option :value="null">请选择服务器...</option>
            <option v-for="server in serversStore.servers" :key="server.id" :value="server.id">
              {{ server.name }}
            </option>
          </select>
        </div>
        <div class="col-auto">
          <button 
            class="btn btn-outline-secondary" 
            @click="handleTestServer" 
            :disabled="!selectedServerId || serversStore.loading"
          >
            <span v-if="testing" class="spinner-border spinner-border-sm me-2" role="status"></span>
            测试连接
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useServersStore } from '@/stores/servers'

const props = defineProps({
  modelValue: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'change', 'test'])

const serversStore = useServersStore()
const selectedServerId = ref(props.modelValue)
const testing = ref(false)

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  selectedServerId.value = newVal
})

// 监听内部值变化
watch(selectedServerId, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleServerChange = () => {
  emit('change', selectedServerId.value)
  if (selectedServerId.value) {
    serversStore.setCurrentServer(selectedServerId.value)
  }
}

const handleTestServer = async () => {
  if (!selectedServerId.value) return
  
  testing.value = true
  try {
    await serversStore.testServer(selectedServerId.value)
    emit('test', selectedServerId.value)
  } catch (error) {
    alert('连接测试失败: ' + error.message)
  } finally {
    testing.value = false
  }
}

onMounted(async () => {
  try {
    await serversStore.loadServers()
    if (serversStore.servers.length > 0 && !selectedServerId.value) {
      // 如果没有选中值，使用 store 中的当前服务器或第一个服务器
      const defaultId = serversStore.currentServerId || serversStore.servers[0].id
      selectedServerId.value = defaultId
      if (defaultId) {
        serversStore.setCurrentServer(defaultId)
      }
    }
  } catch (error) {
    console.error('加载服务器列表失败:', error)
  }
})
</script>

