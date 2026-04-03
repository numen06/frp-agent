<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">API Key 管理</h3>
        <div class="card-actions">
          <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700" @click.stop="openCreateDialog">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14M5 12h14" />
            </svg>
            创建密钥
          </button>
        </div>
      </div>
      <div v-if="loading" class="card-body">
        <div class="text-center py-4">
          <div class="spinner-border spinner-border-sm" role="status"></div>
          <span class="ms-2 text-muted">加载中...</span>
        </div>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full border-collapse text-left text-sm text-gray-700">
          <thead>
            <tr>
              <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200" style="min-width:140px">描述</th>
              <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200" style="min-width:200px">密钥</th>
              <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200 whitespace-nowrap" style="min-width:160px">过期时间</th>
              <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200" style="min-width:70px">状态</th>
              <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200 whitespace-nowrap" style="min-width:160px">创建时间</th>
              <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200 whitespace-nowrap" style="min-width:160px">最后使用</th>
              <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200 whitespace-nowrap" style="min-width:180px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="keys.length === 0">
              <td colspan="7" class="text-center text-muted py-8">
                暂无 API Key，点击上方按钮创建
              </td>
            </tr>
            <tr v-else v-for="key in keys" :key="key.id" :class="rowClass(key)">
              <td class="px-4 py-3 border-b border-gray-100 align-middle">
                <div class="flex items-center gap-2">
                  <span class="truncate" :title="key.description">{{ key.description }}</span>
                  <span v-if="apiKeysStore.selectedKeyId === key.id" class="badge bg-blue shrink-0">默认</span>
                </div>
              </td>
              <td class="px-4 py-3 border-b border-gray-100 align-middle">
                <div class="flex items-center gap-1">
                  <code class="flex-1 text-xs text-gray-600 truncate">{{ key.key }}</code>
                  <button
                    class="inline-flex shrink-0 items-center justify-center rounded p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                    title="复制完整密钥"
                    @click.stop="copyFullKey(key, $event)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                  </button>
                </div>
              </td>
              <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">
                <span v-if="key.expires_at">{{ formatDateTime(key.expires_at) }}</span>
                <span v-else class="text-gray-400">永不过期</span>
              </td>
              <td class="px-4 py-3 border-b border-gray-100 align-middle">
                <span v-if="key.is_expired" class="badge bg-red">已过期</span>
                <span v-else-if="!key.is_active" class="badge bg-secondary">已禁用</span>
                <span v-else class="badge bg-success">正常</span>
              </td>
              <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">{{ formatDateTime(key.created_at) }}</td>
              <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">
                <span v-if="key.last_used_at">{{ formatDateTime(key.last_used_at) }}</span>
                <span v-else class="text-gray-400">从未使用</span>
              </td>
              <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">
                <div class="flex items-center gap-1.5">
                  <button
                    class="inline-flex h-8 items-center justify-center rounded-lg border px-2.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40"
                    :class="apiKeysStore.selectedKeyId === key.id ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
                    :disabled="!key.is_active || key.is_expired || apiKeysStore.selectedKeyId === key.id"
                    title="设为默认"
                    @click="setDefaultKey(key)"
                  >默认</button>
                  <button
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-600 transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-40"
                    :disabled="key.is_expired"
                    title="编辑"
                    @click="editKey(key)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L8.25 18.463 4 20l1.537-4.25 11.325-11.263z"></path>
                    </svg>
                  </button>
                  <button
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-600 transition-colors hover:bg-red-100"
                    title="删除"
                    @click="deleteKey(key)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M3 6h18M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-1 0v14a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V6m-4 0v14a1 1 0 0 0 1 1h2"></path>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <Teleport to="body">
      <div class="modal-backdrop fade show" v-if="dialogVisible" @click="closeDialog"></div>
      <div class="modal modal-blur fade" :class="{ show: dialogVisible }" tabindex="-1" role="dialog" @click.self="closeDialog">
        <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">{{ editingKey ? '编辑 API Key' : '创建 API Key' }}</h5>
              <button type="button" class="btn-close" @click="closeDialog"></button>
            </div>
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label required">描述</label>
                <input
                  type="text"
                  class="form-control"
                  v-model="formData.description"
                  placeholder="请输入密钥描述，用于标识用途"
                  maxlength="200"
                  ref="descInput"
                />
              </div>
              <div class="mb-3">
                <label class="form-label">过期时间</label>
                <input
                  type="datetime-local"
                  class="form-control mb-2"
                  v-model="formData.expires_at"
                />
                <div class="d-flex flex-wrap gap-1">
                  <button
                    type="button"
                    class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                    @click="setExpiresDays(7)"
                  >7天</button>
                  <button
                    type="button"
                    class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                    @click="setExpiresDays(30)"
                  >30天</button>
                  <button
                    type="button"
                    class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                    @click="setExpiresDays(90)"
                  >90天</button>
                  <button
                    type="button"
                    class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                    @click="setExpiresDays(180)"
                  >180天</button>
                  <button
                    type="button"
                    class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                    @click="setExpiresDays(365)"
                  >1年</button>
                  <button
                    type="button"
                    class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                    @click="clearExpiresAt"
                  >永不过期</button>
                </div>
                <small class="form-hint">留空表示永不过期，或使用快捷选项</small>
              </div>
              <div v-if="editingKey" class="mb-3">
                <label class="form-label">状态</label>
                <div>
                  <label class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" v-model="formData.is_active" />
                    <span class="form-check-label">启用</span>
                  </label>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300" @click="closeDialog">取消</button>
              <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50" @click="saveKey" :disabled="!formData.description?.trim() || saving">
                {{ saving ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 创建成功对话框（显示完整密钥） -->
    <Teleport to="body">
      <div class="modal-backdrop fade show" v-if="showKeyDialog" @click="showKeyDialog = false"></div>
      <div class="modal modal-blur fade" :class="{ show: showKeyDialog }" tabindex="-1" role="dialog" @click.self="showKeyDialog = false">
        <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">API Key 创建成功</h5>
              <button type="button" class="btn-close" @click="showKeyDialog = false"></button>
            </div>
            <div class="modal-body">
              <div class="alert alert-warning" role="alert">
                <strong>重要提示：</strong>请妥善保管此密钥，创建后将无法再次查看完整密钥！
              </div>
              <div class="mb-3">
                <label class="form-label">描述</label>
                <p class="form-control-plaintext">{{ createdKeyData?.description }}</p>
              </div>
              <div class="mb-3">
                <label class="form-label">API Key</label>
                <div class="input-group">
                  <input
                    type="text"
                    class="form-control font-monospace"
                    :value="createdKeyData?.key"
                    readonly
                    ref="keyInput"
                  />
                  <button
                    class="inline-flex items-center justify-center gap-2 rounded-r-lg border border-l-0 border-gray-300 px-3 text-gray-700 transition-colors hover:bg-gray-100"
                    type="button"
                    @click.stop="copyCreatedKey($event)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    复制
                  </button>
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label">使用方式</label>
                <div class="card">
                  <div class="card-body">
                    <div class="mb-2">
                      <strong>Header 认证</strong>
                      <div class="mt-1">
                        <code class="text-muted">Authorization: Bearer {{ createdKeyData?.key }}</code>
                      </div>
                    </div>
                    <div class="mb-0">
                      <strong>URL 参数</strong>
                      <div class="mt-1">
                        <code class="text-muted">?api_key={{ createdKeyData?.key }}</code>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700" @click="showKeyDialog = false">我已保存</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 提示消息 -->
    <div v-if="toastMessage" class="position-fixed top-0 inset-e-0 p-3" style="z-index: 1050; min-width: 300px;">
      <div class="alert alert-dismissible" :class="toastType === 'success' ? 'alert-success' : 'alert-danger'" role="alert">
        {{ toastMessage }}
        <a class="btn-close" @click="toastMessage = ''" aria-label="close"></a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { apiKeysApi } from '@/api/apiKeys'
import { useApiKeysStore } from '@/stores/apiKeys'
import { useModal } from '@/composables/useModal'
import { copyWithTooltip } from '@/composables/useCopyTooltip'

const apiKeysStore = useApiKeysStore()
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showKeyDialog = ref(false)
const editingKey = ref(null)
const createdKeyData = ref(null)
const keyInput = ref(null)
const descInput = ref(null)

const formData = ref({
  description: '',
  expires_at: '',
  is_active: true
})

const keys = computed(() => apiKeysStore.keys || [])

const dialogVisible = computed(() => showCreateDialog.value || showEditDialog.value)

const rowClass = (key) => {
  if (key.is_expired) return 'bg-red-50/40'
  if (!key.is_active) return 'bg-gray-50/50'
  return ''
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Toast
const toastMessage = ref('')
const toastType = ref('success')
let toastTimer = null

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMessage.value = ''; toastTimer = null }, 3000)
}

// 加载列表
const loadKeys = async () => {
  loading.value = true
  try {
    await apiKeysStore.loadKeys()
  } catch (e) {
    console.error('加载 API Key 列表失败:', e)
    showToast('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

// 复制完整密钥（从列表）
const copyFullKey = async (key, event) => {
  try {
    const fullKey = await apiKeysStore.resolveFullKey(key.id)
    if (!fullKey) {
      showToast('无法获取完整密钥', 'error')
      return
    }
    await copyWithTooltip(fullKey, event)
  } catch (e) {
    showToast('复制失败: ' + (e.response?.data?.detail || e.message), 'error')
  }
}

// 复制创建后的密钥
const copyCreatedKey = async (event) => {
  if (createdKeyData.value?.key) {
    await copyWithTooltip(createdKeyData.value.key, event)
  }
}

// 设为默认
const setDefaultKey = (key) => {
  if (!key.is_active || key.is_expired) return
  apiKeysStore.setDefaultKey(key.id)
  showToast(`已将 "${key.description}" 设为默认`, 'success')
}

// 过期时间
const setExpiresDays = (days) => {
  const d = new Date()
  d.setDate(d.getDate() + days)
  const pad = (n) => String(n).padStart(2, '0')
  formData.value.expires_at = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const clearExpiresAt = () => {
  formData.value.expires_at = ''
}

// 对话框操作
const openCreateDialog = () => {
  showCreateDialog.value = true
  nextTick(() => descInput.value?.focus())
}

const closeDialog = () => {
  showCreateDialog.value = false
  showEditDialog.value = false
  editingKey.value = null
  formData.value = { description: '', expires_at: '', is_active: true }
}

const editKey = (key) => {
  editingKey.value = key
  formData.value = {
    description: key.description,
    expires_at: key.expires_at ? new Date(key.expires_at).toISOString().slice(0, 16) : '',
    is_active: key.is_active
  }
  showEditDialog.value = true
  nextTick(() => descInput.value?.focus())
}

// 保存
const saveKey = async () => {
  if (!formData.value.description?.trim()) return
  saving.value = true
  try {
    const data = {
      description: formData.value.description.trim(),
      expires_at: formData.value.expires_at ? new Date(formData.value.expires_at).toISOString() : null
    }

    if (editingKey.value) {
      data.is_active = formData.value.is_active
      await apiKeysApi.update(editingKey.value.id, data)
      await loadKeys()
      closeDialog()
      showToast('更新成功')
    } else {
      const result = await apiKeysApi.create(data)
      if (!result?.id || !result?.key) {
        showToast('创建失败：服务器返回数据不完整', 'error')
        return
      }
      const keyValue = String(result.key).trim()
      const idNum = Number(result.id)
      if (keyValue === String(idNum) || keyValue.length < 20) {
        showToast('创建失败：服务器返回数据异常', 'error')
        return
      }
      localStorage.setItem(`api_key_${idNum}`, keyValue)
      localStorage.setItem(`api_key_${String(idNum)}`, keyValue)

      createdKeyData.value = result
      closeDialog()
      showKeyDialog.value = true
      if (!apiKeysStore.selectedKeyId) {
        apiKeysStore.setDefaultKey(idNum)
        showToast('已自动设为默认密钥')
      }
      await loadKeys()
    }
  } catch (e) {
    console.error('保存失败:', e)
    showToast('保存失败: ' + e.message, 'error')
  } finally {
    saving.value = false
  }
}

// 删除
const deleteKey = async (key) => {
  if (!confirm(`确定要删除密钥 "${key.description}" 吗？此操作不可恢复。`)) return
  try {
    await apiKeysApi.delete(key.id)
    if (apiKeysStore.selectedKeyId === key.id) {
      apiKeysStore.setDefaultKey(null)
    }
    await loadKeys()
    showToast('删除成功')
  } catch (e) {
    showToast('删除失败: ' + e.message, 'error')
  }
}

useModal(dialogVisible, closeDialog)
useModal(showKeyDialog, () => { showKeyDialog.value = false })

onMounted(() => {
  loadKeys()
})
</script>
