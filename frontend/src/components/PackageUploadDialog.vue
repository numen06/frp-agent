<template>
  <Teleport to="body">
    <template v-if="visible">
      <div class="modal-backdrop fade show" @click="closeDialog"></div>
      <div
        class="modal modal-blur fade show"
        tabindex="-1"
        role="dialog"
        aria-modal="true"
        @click.self="closeDialog"
      >
        <div class="modal-dialog modal-dialog-centered" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">手动上传安装包</h5>
              <button type="button" class="btn-close" aria-label="关闭" @click="closeDialog"></button>
            </div>
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label">安装包文件</label>
                <div
                  class="flex min-h-[8.5rem] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-6 text-center text-sm text-gray-600 transition-colors hover:border-blue-400 hover:bg-blue-50/40"
                  :class="{
                    'border-blue-500 bg-blue-50/60': isDragging,
                    'border-green-400 bg-green-50/50': !!file && !isDragging
                  }"
                  @click="triggerFileInput"
                  @dragenter.prevent="onDragEnter"
                  @dragover.prevent="onDragOver"
                  @dragleave.prevent="onDragLeave"
                  @drop.prevent="onDrop"
                >
                  <input ref="fileInputRef" class="d-none" type="file" accept=".zip,.gz,.tgz,.xz" @change="onFileChange" />
                  <template v-if="file">
                    <span class="font-medium text-gray-900 break-all">{{ file.name }}</span>
                    <span class="text-muted" style="font-size: 0.8rem">{{ formatSize(file.size) }}</span>
                    <span class="text-muted" style="font-size: 0.75rem">点击可重新选择</span>
                  </template>
                  <template v-else>
                    <span>拖拽文件到此处，或点击选择</span>
                    <span class="text-muted" style="font-size: 0.8rem">官方包名如 frp_0.61.1_linux_amd64.tar.gz 将自动填写版本与平台</span>
                  </template>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label">版本</label>
                <input v-model="version" class="form-control" type="text" placeholder="例如 v0.61.1（可选，可由文件名识别）" />
              </div>
              <div class="mb-0">
                <label class="form-label">平台</label>
                <select v-model="platform" class="form-control">
                  <option value="">请选择或自动识别</option>
                  <option v-for="p in props.platforms" :key="p" :value="p">{{ p }}</option>
                </select>
                <p v-if="parsedFromFilename" class="form-hint mt-1 mb-0 text-muted" style="font-size: 0.8rem">
                  已根据文件名填入，可自行修改。
                </p>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn" @click="closeDialog">取消</button>
              <button type="button" class="btn btn-primary" :disabled="loading" @click="submit">
                {{ loading ? '上传中...' : '上传' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  platforms: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'submit'])

const visible = ref(false)
const version = ref('')
const platform = ref('')
const file = ref(null)
const fileInputRef = ref(null)
const isDragging = ref(false)
const parsedFromFilename = ref(null)

watch(() => props.modelValue, (val) => {
  visible.value = val
})
watch(visible, (val) => emit('update:modelValue', val))

watch(visible, (open) => {
  if (!open) {
    version.value = ''
    platform.value = ''
    file.value = null
    parsedFromFilename.value = null
    isDragging.value = false
    dragCounter = 0
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
})

const closeDialog = () => {
  visible.value = false
}
useModal(visible, closeDialog)

function parseFilename(filename) {
  if (!filename) return null
  const re = /^frp_(\d+\.\d+\.\d+)_(.+)\.(?:tar\.gz|tgz|zip|tar\.xz)$/i
  const m = filename.match(re)
  if (!m) return null
  return { version: `v${m[1]}`, platform: m[2] }
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function applyFile(selectedFile) {
  file.value = selectedFile
  const parsed = parseFilename(selectedFile.name)
  parsedFromFilename.value = parsed
  if (parsed) {
    version.value = parsed.version
    platform.value = parsed.platform
  }
}

const onFileChange = (e) => {
  const f = e.target.files?.[0]
  if (f) applyFile(f)
}

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

let dragCounter = 0
const onDragEnter = () => {
  dragCounter++
  isDragging.value = true
}
const onDragOver = () => {
  isDragging.value = true
}
const onDragLeave = () => {
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    isDragging.value = false
  }
}
const onDrop = (e) => {
  dragCounter = 0
  isDragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) applyFile(f)
}

const submit = () => {
  if (!file.value) {
    alert('请选择文件')
    return
  }
  emit('submit', { version: version.value?.trim() || '', platform: platform.value?.trim() || '', file: file.value })
}
</script>
