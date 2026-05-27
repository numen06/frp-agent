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
        class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-5xl flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(92vh,800px)] sm:rounded-xl"
        @click.stop
      >
        <div class="sticky top-0 z-10 flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-3.5 sm:px-5">
          <h2 class="text-lg font-semibold text-gray-900">平台脚本模板编辑</h2>
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
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 text-sm sm:px-5">
          <div class="grid gap-4">
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700">目标平台</label>
              <select
                v-model="platform"
                class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              >
                <option value="">请选择平台</option>
                <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="code-editor-wrapper min-h-[200px] overflow-x-auto">
              <CodeEditor
                v-model="content"
                language="shell"
                :height="editorHeight"
                placeholder="可用变量：{{filename}} {{download_url}} {{install_path}} {{config_line}} {{platform}} {{version}}"
              />
            </div>
          </div>
        </div>
        <div class="sticky bottom-0 z-10 flex shrink-0 flex-col gap-2 border-t border-gray-200 bg-gray-50 px-4 py-3.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:gap-2 sm:px-5">
          <button
            type="button"
            class="btn btn-md btn-outline-primary w-full sm:w-auto"
            @click="loadTemplate"
          >
            加载模板
          </button>
          <button
            type="button"
            class="btn btn-md btn-primary w-full sm:w-auto"
            :disabled="saving"
            @click="saveTemplate"
          >
            {{ saving ? '保存中...' : '保存模板' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useModal } from '@/composables/useModal'
import CodeEditor from '@/components/CodeEditor.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  platforms: { type: Array, default: () => [] },
  templates: { type: Object, default: () => ({}) },
  saving: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'save'])
const visible = ref(false)
const platform = ref('')
const content = ref('')
const editorHeight = ref('420px')

const updateEditorHeight = () => {
  editorHeight.value = window.matchMedia('(max-width: 639px)').matches ? '240px' : '420px'
}

onMounted(() => {
  updateEditorHeight()
  window.addEventListener('resize', updateEditorHeight)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateEditorHeight)
})

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => emit('update:modelValue', val))

const closeDialog = () => { visible.value = false }
useModal(visible, closeDialog)

const loadTemplate = () => {
  if (!platform.value) {
    alert('请先选择平台')
    return
  }
  content.value = props.templates[platform.value] || ''
}

const saveTemplate = () => {
  if (!platform.value || !content.value.trim()) {
    alert('请选择平台并填写脚本内容')
    return
  }
  emit('save', { platform: platform.value, content: content.value })
}
</script>

<style scoped>
.code-editor-wrapper {
  border-radius: 8px;
  overflow: hidden;
}
</style>
