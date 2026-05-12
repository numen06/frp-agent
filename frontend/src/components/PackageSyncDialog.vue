<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @click.self="closeDialog"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="closeDialog"></div>
      <div
        class="relative z-10 flex max-h-[min(90vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl will-change-transform"
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
        <div class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-5 py-3.5">
          <button
            type="button"
            class="mr-auto inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            @click="closeDialog"
          >
            取消
          </button>
          <button
            type="button"
            class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="loading"
            @click="submit"
          >
            {{ loading ? '同步中...' : '开始同步' }}
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
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'submit'])
const visible = ref(false)
const form = reactive({
  version: '',
  platforms: []
})

const platformsForVersion = computed(() => {
  const rel = props.releases.find((r) => r.version === form.version)
  return rel?.platforms?.length ? rel.platforms : []
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
  emit('submit', { version: form.version, platforms: form.platforms })
}
</script>
