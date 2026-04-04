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
        <div class="modal-dialog modal-dialog-centered modal-lg" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">上传安装包</h5>
              <button type="button" class="btn-close" aria-label="关闭" @click="closeDialog"></button>
            </div>
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label">选择文件（支持多选）</label>
                <div
                  v-bind="getRootProps()"
                  class="flex min-h-34 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-6 text-center text-sm text-gray-600 transition-colors hover:border-blue-400 hover:bg-blue-50/40"
                  :class="{
                    'border-blue-500 bg-blue-50/60': isDragActive,
                    'border-red-400 bg-red-50/50': isDragReject,
                    'border-green-400 bg-green-50/50': fileList.length > 0 && !isDragActive && !isDragReject
                  }"
                >
                  <input v-bind="getInputProps()" />
                  <template v-if="fileList.length === 0">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-gray-400" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21H7a2 2 0 0 1 -2 -2V5a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"/><path d="M12 11l0 6"/><path d="M9.5 13.5l2.5 -2.5l2.5 2.5"/>
                    </svg>
                    <span v-if="isDragReject" class="text-red-500 font-medium">不支持该文件类型</span>
                    <span v-else>拖拽文件到此处，或点击选择文件</span>
                    <span class="text-muted" style="font-size: 0.8rem">支持批量选择多个安装包（.zip, .gz, .tgz, .xz）</span>
                    <span class="text-muted" style="font-size: 0.75rem">官方包名如 frp_0.61.1_linux_amd64.tar.gz 将自动解析版本与平台</span>
                  </template>
                  <template v-else>
                    <span class="font-medium text-green-700">已选择 {{ fileList.length }} 个文件</span>
                    <span class="text-muted" style="font-size: 0.8rem">点击或拖拽可继续添加文件</span>
                  </template>
                </div>
                <p v-if="fileRejections.length" class="text-danger mt-1 mb-0" style="font-size: 0.8rem">
                  {{ fileRejections.map(r => `${r.file.name}: ${r.errors.map(e => e.message).join(', ')}`).join('; ') }}
                </p>
              </div>

              <div v-if="fileList.length > 0" class="mb-3">
                <div class="flex items-center justify-between mb-2">
                  <label class="form-label mb-0">文件列表</label>
                  <button type="button" class="btn btn-sm btn-ghost text-danger" @click="clearAll">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline-block align-text-bottom" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 7l16 0"/><path d="M10 11l0 6"/><path d="M14 11l0 6"/><path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"/><path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"/>
                    </svg>
                    清空
                  </button>
                </div>
                <div class="max-h-72 overflow-y-auto rounded-lg border border-gray-200">
                  <table class="w-full text-sm text-left">
                    <thead>
                      <tr class="bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">
                        <th class="px-3 py-2">文件名</th>
                        <th class="px-3 py-2 w-20 text-center">大小</th>
                        <th class="px-3 py-2 w-24 text-center">版本</th>
                        <th class="px-3 py-2 w-36 text-center">平台</th>
                        <th class="px-3 py-2 w-10"></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(item, idx) in fileList" :key="item.id" class="border-b border-gray-100 last:border-b-0 hover:bg-gray-50">
                        <td class="px-3 py-2">
                          <div class="font-medium text-gray-900 truncate" :title="item.file.name">{{ item.file.name }}</div>
                          <div v-if="!item.parsed" class="text-danger mt-0.5" style="font-size: 0.7rem">无法自动解析版本/平台</div>
                        </td>
                        <td class="px-3 py-2 text-muted text-center whitespace-nowrap" style="font-size: 0.8rem">{{ formatSize(item.file.size) }}</td>
                        <td class="px-3 py-2 text-center">
                          <span v-if="item.parsed" class="badge bg-blue text-white" style="font-size: 0.7rem">{{ item.parsed.version }}</span>
                          <span v-else class="text-gray-400">-</span>
                        </td>
                        <td class="px-3 py-2 text-center">
                          <span v-if="item.parsed" class="badge bg-green text-white" style="font-size: 0.7rem">{{ item.parsed.platform }}</span>
                          <span v-else class="text-gray-400">-</span>
                        </td>
                        <td class="px-3 py-2 text-center">
                          <button
                            type="button"
                            class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-gray-400 transition-colors hover:bg-red-50 hover:text-red-500"
                            title="移除"
                            @click="removeFile(idx)"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M18 6l-12 12"/><path d="M6 6l12 12"/>
                            </svg>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <template v-if="fileList.length === 1">
                <div class="mb-3">
                  <label class="form-label">版本</label>
                  <input v-model="manualVersion" class="form-control" type="text" placeholder="例如 v0.61.1（可选，可由文件名识别）" />
                </div>
                <div class="mb-0">
                  <label class="form-label">平台</label>
                  <select v-model="manualPlatform" class="form-control">
                    <option value="">请选择或自动识别</option>
                    <option v-for="p in props.platforms" :key="p" :value="p">{{ p }}</option>
                  </select>
                  <p v-if="fileList[0]?.parsed" class="form-hint mt-1 mb-0 text-muted" style="font-size: 0.8rem">
                    已根据文件名填入，可自行修改。
                  </p>
                </div>
              </template>

              <div v-if="unparsedCount > 0" class="alert alert-warning mb-0" style="font-size: 0.85rem">
                <strong>注意：</strong>{{ unparsedCount }} 个文件无法从文件名自动解析版本/平台，批量上传时将跳过这些文件。
                <template v-if="unparsedNames.length > 0">
                  <br /><span class="text-muted">{{ unparsedNames.join('、') }}</span>
                </template>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn" @click="closeDialog">取消</button>
              <button
                v-if="fileList.length === 1"
                type="button"
                class="btn btn-primary"
                :disabled="loading || fileList.length === 0 || (!manualVersion && !manualPlatform)"
                @click="submit"
              >
                {{ loading ? '上传中...' : '上传' }}
              </button>
              <button
                v-else
                type="button"
                class="btn btn-primary"
                :disabled="loading || fileList.length === 0 || parsedCount === 0"
                @click="submit"
              >
                {{ loading ? '上传中...' : `批量上传 (${parsedCount}/${fileList.length} 个文件)` }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useDropzone } from 'vue3-dropzone'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  platforms: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'submit', 'submit-batch'])

const visible = ref(false)
const fileList = ref([])
const manualVersion = ref('')
const manualPlatform = ref('')

let fileIdCounter = 0
function makeId() {
  return ++fileIdCounter
}

function parseFilename(filename) {
  if (!filename) return null
  const re = /^frp_(\d+\.\d+\.\d+)_(.+)\.(?:tar\.gz|tgz|zip|tar\.xz)$/i
  const m = filename.match(re)
  if (!m) return null
  return { version: `v${m[1]}`, platform: m[2] }
}

function formatSize(bytes) {
  if (!bytes || bytes < 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const onDropAccepted = (files) => {
  for (const f of files) {
    const parsed = parseFilename(f.name)
    fileList.value.push({ file: f, parsed, id: makeId() })
  }
  if (fileList.value.length === 1) {
    const first = fileList.value[0]
    if (first.parsed) {
      manualVersion.value = first.parsed.version
      manualPlatform.value = first.parsed.platform
    }
  }
}

const { getRootProps, getInputProps, isDragActive, isDragReject, fileRejections } = useDropzone({
  accept: '.zip,.gz,.tgz,.xz',
  multiple: true,
  noClick: false,
  noDrag: false,
  onDropAccepted
})

watch(() => props.modelValue, (val) => {
  visible.value = val
})
watch(visible, (val) => emit('update:modelValue', val))

watch(visible, (open) => {
  if (!open) {
    fileList.value = []
    manualVersion.value = ''
    manualPlatform.value = ''
    fileIdCounter = 0
  }
})

const closeDialog = () => {
  visible.value = false
}
useModal(visible, closeDialog)

const removeFile = (idx) => {
  fileList.value.splice(idx, 1)
  if (fileList.value.length === 1) {
    const first = fileList.value[0]
    if (first.parsed) {
      manualVersion.value = first.parsed.version
      manualPlatform.value = first.parsed.platform
    }
  } else if (fileList.value.length === 0) {
    manualVersion.value = ''
    manualPlatform.value = ''
  }
}

const clearAll = () => {
  fileList.value = []
  manualVersion.value = ''
  manualPlatform.value = ''
}

const parsedCount = computed(() => fileList.value.filter(i => i.parsed).length)
const unparsedCount = computed(() => fileList.value.filter(i => !i.parsed).length)
const unparsedNames = computed(() => fileList.value.filter(i => !i.parsed).map(i => i.file.name))

const submit = () => {
  if (fileList.value.length === 0) return
  if (fileList.value.length === 1) {
    const item = fileList.value[0]
    emit('submit', {
      version: manualVersion.value?.trim() || '',
      platform: manualPlatform.value?.trim() || '',
      file: item.file
    })
  } else {
    const parsedFiles = fileList.value.filter(i => i.parsed)
    if (parsedFiles.length === 0) return
    emit('submit-batch', { files: parsedFiles.map(i => i.file) })
  }
}
</script>
