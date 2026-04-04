<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-backdrop fade show" @click="closeDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: visible }" tabindex="-1" role="dialog" @click.self="closeDialog">
      <div class="modal-dialog modal-dialog-centered" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">手动上传安装包</h5>
            <button type="button" class="btn-close" @click="closeDialog"></button>
          </div>
          <div class="modal-body">
            <!-- 拖拽上传区域 -->
            <div
              class="upload-dropzone mb-3"
              :class="{ 'drag-over': isDragging, 'has-file': !!file }"
              @click="triggerFileInput"
              @dragenter.prevent="onDragEnter"
              @dragover.prevent="onDragOver"
              @dragleave.prevent="onDragLeave"
              @drop.prevent="onDrop"
            >
              <input ref="fileInputRef" class="d-none" type="file" @change="onFileChange" />
              <template v-if="file">
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-lg mb-2 text-green" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M5 12l5 5l10 -10" />
                </svg>
                <div class="text-truncate" style="max-width: 100%;">{{ file.name }}</div>
                <div class="text-muted" style="font-size: 0.8rem;">{{ formatSize(file.size) }}</div>
              </template>
              <template v-else>
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-lg mb-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M7 18a4.6 4.4 0 0 1 0 -9h0a5 5 0 0 1 11 2h1a3.5 3.5 0 0 1 0 7h-12" />
                  <path d="M12 13v8" />
                  <path d="M9 18l3 3l3 -3" />
                </svg>
                <div>拖拽文件到此处，或点击选择文件</div>
                <div class="text-muted" style="font-size: 0.8rem;">支持官方 frp 安装包，自动识别版本和平台</div>
              </template>
            </div>

            <div class="row g-3">
              <div class="col-6">
                <label class="form-label">版本</label>
                <input v-model="version" class="form-control" type="text" placeholder="例如 v0.61.1" />
              </div>
              <div class="col-6">
                <label class="form-label">平台</label>
                <select v-model="platform" class="form-control">
                  <option value="">请选择平台</option>
                  <option v-for="p in props.platforms" :key="p" :value="p">{{ p }}</option>
                </select>
              </div>
            </div>
            <div v-if="parsedFromFilename" class="mt-2" style="font-size: 0.8rem;">
              <span class="text-muted">已从文件名自动识别：</span>
              <span class="badge bg-secondary-lt">{{ parsedFromFilename.version }}</span>
              <span class="badge bg-secondary-lt">{{ parsedFromFilename.platform }}</span>
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
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
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

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => emit('update:modelValue', val))

const closeDialog = () => { visible.value = false }
useModal(visible, closeDialog)

// 从文件名解析版本和平台
function parseFilename(filename) {
  if (!filename) return null
  const re = /^frp_(\d+\.\d+\.\d+)_(.+)\.(?:tar\.gz|tgz|zip|tar\.xz)$/i
  const m = filename.match(re)
  if (!m) return null
  return { version: `v${m[1]}`, platform: m[2] }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
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
const onDragEnter = () => { dragCounter++; isDragging.value = true }
const onDragOver = () => { isDragging.value = true }
const onDragLeave = () => { dragCounter--; if (dragCounter <= 0) { dragCounter = 0; isDragging.value = false } }
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
  emit('submit', { version: version.value, platform: platform.value, file: file.value })
}
</script>

<style scoped>
.upload-dropzone {
  border: 2px dashed var(--tblr-border-color, #d1d5db);
  border-radius: 0.5rem;
  padding: 2rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--tblr-body-bg, #fff);
  user-select: none;
}
.upload-dropzone:hover {
  border-color: var(--tblr-primary, #206bc4);
  background: rgba(32, 107, 196, 0.03);
}
.upload-dropzone.drag-over {
  border-color: var(--tblr-primary, #206bc4);
  background: rgba(32, 107, 196, 0.08);
  transform: scale(1.01);
}
.upload-dropzone.has-file {
  border-color: #2fb344;
  background: rgba(47, 179, 68, 0.04);
  cursor: default;
}
</style>
