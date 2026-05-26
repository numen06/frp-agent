<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @click.self="closeDialog"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="closeDialog"></div>
      <div
        class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(90vh,640px)] sm:rounded-xl"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-5 py-3.5">
          <h2 class="text-lg font-semibold text-gray-900">从 GitHub 同步安装包</h2>
          <button
            type="button"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
            aria-label="关闭"
            @click="closeDialog"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">版本</label>
            <select
              v-model="form.version"
              class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            >
              <option value="">请选择版本</option>
              <option v-for="item in releases" :key="item.version" :value="item.version">
                {{ item.version }}
              </option>
            </select>
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">下载通道</label>
            <div class="grid grid-cols-2 overflow-hidden rounded-lg border border-gray-300 bg-white text-sm">
              <button
                type="button"
                class="px-3 py-2 font-medium transition-colors"
                :class="form.download_source === 'origin' ? 'bg-blue-600 text-white' : 'text-gray-700 hover:bg-gray-50'"
                @click="form.download_source = 'origin'"
              >
                源地址
              </button>
              <button
                type="button"
                class="border-l border-gray-300 px-3 py-2 font-medium transition-colors"
                :class="form.download_source === 'accelerated' ? 'bg-blue-600 text-white' : 'text-gray-700 hover:bg-gray-50'"
                @click="form.download_source = 'accelerated'"
              >
                国内加速下载
              </button>
            </div>
          </div>
          <div class="mb-0">
            <label class="mb-1 block text-sm font-medium text-gray-700">平台（可多选）</label>
            <div v-if="platformsForVersion.length" class="mb-2 flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-lg border border-blue-600 px-2.5 py-1.5 text-xs font-medium text-blue-600 transition-colors hover:bg-blue-50"
                @click="selectAll"
              >
                全选
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50"
                @click="deselectAll"
              >
                取消全选
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50"
                @click="invertSelection"
              >
                反选
              </button>
              <span class="ml-auto text-xs font-medium text-gray-600">已选 {{ form.platforms.length }} / {{ platformsForVersion.length }}</span>
            </div>
            <div class="grid max-h-[260px] gap-2 overflow-y-auto">
              <label v-for="p in platformsForVersion" :key="p" class="flex cursor-pointer items-center gap-2 rounded-lg border border-gray-100 px-2 py-1.5 hover:bg-gray-50">
                <input v-model="form.platforms" class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" type="checkbox" :value="p" />
                <span class="text-sm text-gray-800">{{ p }}</span>
              </label>
            </div>
          </div>
        </div>
        <div
          v-if="loading && progress.total > 0"
          class="shrink-0 border-t border-gray-100 bg-blue-50 px-5 py-2.5 text-xs text-blue-800"
        >
          后台下载中… {{ progress.completed }} / {{ progress.total }}
          <span v-if="progress.status === 'running'" class="ml-1">（可关闭此窗口，任务仍在继续）</span>
        </div>
        <div class="flex shrink-0 flex-col-reverse gap-2 border-t border-gray-200 bg-gray-50 px-4 py-3.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:px-5">
          <button
            type="button"
            class="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 sm:mr-auto sm:w-auto sm:py-2"
            @click="closeDialog"
          >
            取消
          </button>
          <button
            type="button"
            class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3.5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:py-2"
            :disabled="loading"
            @click="submit"
          >
            {{ syncButtonLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  releases: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  progress: {
    type: Object,
    default: () => ({ completed: 0, total: 0, status: '' })
  }
})

const emit = defineEmits(['update:modelValue', 'submit'])
const visible = ref(false)
const form = reactive({
  version: '',
  platforms: [],
  download_source: 'origin'
})

const platformsForVersion = computed(() => {
  const rel = props.releases.find((r) => r.version === form.version)
  return rel?.platforms?.length ? rel.platforms : []
})

const syncButtonLabel = computed(() => {
  if (!props.loading) return '开始同步'
  if (props.progress.total > 0) {
    return `下载中 (${props.progress.completed}/${props.progress.total})`
  }
  return '提交中...'
})

watch(() => props.modelValue, (val) => {
  visible.value = val
})
watch(visible, (val) => emit('update:modelValue', val))

watch(
  () => [form.version, props.releases],
  () => {
    const list = platformsForVersion.value
    form.platforms = list.length ? [...list] : []
  },
  { deep: true }
)

const closeDialog = () => {
  visible.value = false
}

useModal(visible, closeDialog)

const selectAll = () => {
  form.platforms = [...platformsForVersion.value]
}
const deselectAll = () => {
  form.platforms = []
}
const invertSelection = () => {
  const all = platformsForVersion.value
  form.platforms = all.filter((p) => !form.platforms.includes(p))
}

const submit = () => {
  if (!form.version) {
    alert('请选择版本')
    return
  }
  emit('submit', { version: form.version, platforms: form.platforms, download_source: form.download_source })
}
</script>
