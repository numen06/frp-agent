<template>
  <div class="mb-5 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
    <div class="border-b border-gray-200 px-3 py-3 sm:px-5 sm:py-3.5">
      <h3 class="text-base font-semibold text-gray-900">服务器选择</h3>
    </div>
    <div class="p-3 sm:p-5">
      <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <label class="text-sm font-medium text-gray-700">当前服务器：</label>
        <div class="min-w-0 w-full flex-1 sm:min-w-[12rem] sm:max-w-md">
          <AppSelect
            class="block w-full"
            :number="true"
            v-model="selectedServerId"
            @change="handleServerChange"
            :disabled="serversStore.loading"
          >
            <option :value="null">请选择服务器...</option>
            <option v-for="server in serversStore.servers" :key="server.id" :value="server.id">
              {{ server.name }}
            </option>
          </AppSelect>
        </div>
        <button
          type="button"
          class="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:pointer-events-none disabled:opacity-50 sm:w-auto"
          @click="handleTestServer"
          :disabled="!selectedServerId || serversStore.loading"
        >
          <span
            v-if="testing"
            class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"
            role="status"
            aria-label="测试中"
          ></span>
          测试连接
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useServersStore } from '@/stores/servers'
import AppSelect from '@/components/AppSelect.vue'

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

watch(() => props.modelValue, (newVal) => {
  selectedServerId.value = newVal
})

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
