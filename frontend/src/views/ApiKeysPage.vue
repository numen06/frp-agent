<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">API Key 管理</h3>
        <div class="card-actions">
          <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700" @click.stop="showCreateDialog = true">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14M5 12h14" />
            </svg>
            创建密钥
          </button>
        </div>
      </div>
      <div v-if="loading" class="card-body">
        <div class="text-center py-4">
          <div class="spinner-border spinner-border-sm" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
        </div>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full border-collapse text-left text-sm text-gray-700">
                <thead>
                  <tr>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">ID</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">密钥</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">描述</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">过期时间</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">状态</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">创建时间</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">最后使用</th>
                    <th class="w-[1%] whitespace-nowrap px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="apiKeys.length === 0">
                    <td colspan="8" class="text-center text-muted py-4">
                      暂无 API Key，点击上方按钮创建
                    </td>
                  </tr>
                   <tr v-else v-for="key in apiKeys" :key="key.id">
                     <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ key.id }}</td>
                     <td class="px-4 py-3 border-b border-gray-100 align-middle">
                       <div class="d-flex align-items-center">
                        <code class="grow me-2 text-gray-700">{{ key.key }}</code>
                         <button 
                           class="inline-flex items-center justify-center rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100"
                           @click.stop="copyKeyFromList(key.id)"
                           :title="hasFullKey(key.id) ? '点击复制完整密钥' : '点击复制密钥（将从服务器获取）'"
                         >
                          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                          </svg>
                         </button>
                       </div>
                     </td>
                     <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <div class="inline-flex items-center gap-2">
                        <span>{{ key.description }}</span>
                        <span v-if="apiKeysStore.selectedKeyId === key.id" class="badge bg-blue">默认</span>
                      </div>
                     </td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <span v-if="key.expires_at">
                        {{ formatDateTime(key.expires_at) }}
                      </span>
                      <span v-else class="text-gray-700">永不过期</span>
                    </td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <span v-if="key.is_expired" class="badge bg-red">已过期</span>
                      <span v-else-if="!key.is_active" class="badge bg-secondary">已禁用</span>
                      <span v-else class="badge bg-success">正常</span>
                    </td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ formatDateTime(key.created_at) }}</td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <span v-if="key.last_used_at">{{ formatDateTime(key.last_used_at) }}</span>
                      <span v-else class="text-gray-700">从未使用</span>
                    </td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <div class="btn-list flex-nowrap">
                        <button
                          class="inline-flex h-8 items-center justify-center rounded-lg border border-blue-200 px-2 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-50"
                          @click="setDefaultKey(key)"
                          :disabled="!key.is_active || key.is_expired || apiKeysStore.selectedKeyId === key.id"
                          title="设为默认"
                          aria-label="设为默认"
                        >
                          默认
                        </button>
                        <button 
                          class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-700 transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50" 
                          @click="editKey(key)"
                          :disabled="key.is_expired"
                          title="编辑"
                          aria-label="编辑"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L8.25 18.463 4 20l1.537-4.25 11.325-11.263z"/>
                          </svg>
                        </button>
                        <button 
                          class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-700 transition-colors hover:bg-red-100" 
                          @click="deleteKey(key)"
                          title="删除"
                          aria-label="删除"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M3 6h18M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-1 0v14a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V6m-4 0v14a1 1 0 0 0 1 1h2"/>
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
      <div class="modal modal-blur fade" :class="{ show: showCreateDialog || showEditDialog }" tabindex="-1" role="dialog">
        <div class="modal-dialog modal-dialog-centered" role="document">
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
                placeholder="请输入密钥描述"
                maxlength="200"
              />
              <small class="form-hint">描述是必填项，用于标识此密钥的用途</small>
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
                  class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(7)"
                  title="7天后过期"
                >
                  7天
                </button>
                <button 
                  type="button" 
                  class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(30)"
                  title="30天后过期"
                >
                  30天
                </button>
                <button 
                  type="button" 
                  class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(90)"
                  title="90天后过期"
                >
                  90天
                </button>
                <button 
                  type="button" 
                  class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(180)"
                  title="180天后过期"
                >
                  180天
                </button>
                <button 
                  type="button" 
                  class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(365)"
                  title="1年后过期"
                >
                  1年
                </button>
                <button 
                  type="button" 
                  class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="clearExpiresAt"
                  title="永不过期"
                >
                  永不过期
                </button>
              </div>
              <small class="form-hint">留空表示永不过期，或使用快捷选项</small>
            </div>
            <div v-if="editingKey" class="mb-3">
              <label class="form-label">状态</label>
              <div>
                <label class="form-check form-check-inline">
                  <input 
                    class="form-check-input" 
                    type="checkbox" 
                    v-model="formData.is_active"
                  />
                  <span class="form-check-label">启用</span>
                </label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300" @click="closeDialog">取消</button>
            <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50" @click="saveKey" :disabled="!formData.description || saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
          </div>
        </div>
      </div>
      <div v-if="showCreateDialog || showEditDialog" class="modal-backdrop fade show" @click="closeDialog"></div>
    </Teleport>

    <!-- 创建成功对话框（显示完整密钥） -->
    <Teleport to="body">
      <div class="modal modal-blur fade" :class="{ show: showKeyDialog }" tabindex="-1" role="dialog">
        <div class="modal-dialog modal-dialog-centered" role="document">
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
                  @click.stop="copyKey"
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
                      <code class="text-muted">
                        Authorization: Bearer {{ createdKeyData?.key }}
                      </code>
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
      <div v-if="showKeyDialog" class="modal-backdrop fade show" @click="showKeyDialog = false"></div>
    </Teleport>

     <!-- 提示消息 -->
     <div v-if="toastMessage" class="position-fixed top-0 inset-e-0 p-3" style="z-index: 1050; min-width: 300px;">
       <div class="alert alert-dismissible" :class="toastType === 'success' ? 'alert-success' : 'alert-danger'" role="alert">
         <h4 class="alert-title">{{ toastType === 'success' ? '成功' : '错误' }}</h4>
         <div>{{ toastMessage }}</div>
         <a class="btn-close" @click="closeToast" aria-label="close"></a>
       </div>
     </div>
   </div>
 </template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { apiKeysApi } from '@/api/apiKeys'
import { useApiKeysStore } from '@/stores/apiKeys'
import { useModal } from '@/composables/useModal'

const apiKeysStore = useApiKeysStore()
const apiKeys = ref([])
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showKeyDialog = ref(false)
const editingKey = ref(null)
const createdKeyData = ref(null)
const keyInput = ref(null)

const formData = ref({
  description: '',
  expires_at: '',
  is_active: true
})

// 加载 API Key 列表
const loadApiKeys = async () => {
  loading.value = true
  try {
    if (apiKeysStore.selectedKeyId === null) {
      apiKeysStore.selectedKeyId = apiKeysStore.getStoredDefaultId()
    }
    await apiKeysStore.loadKeys()
    apiKeys.value = apiKeysStore.keys || []
    // 检查每个密钥是否在 localStorage 中有完整密钥
    apiKeys.value.forEach(key => {
      key.hasFullKey = hasFullKey(key.id)
    })
  } catch (error) {
    console.error('加载 API Key 列表失败:', error)
    alert('加载失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const setDefaultKey = (key) => {
  if (!key?.is_active || key?.is_expired) {
    alert('只能将激活且未过期的 API Key 设为默认')
    return
  }
  apiKeysStore.setDefaultKey(key.id)
  showToast(`已将 "${key.description}" 设为默认 API Key`, 'success')
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 设置过期天数
const setExpiresDays = (days) => {
  const now = new Date()
  now.setDate(now.getDate() + days)
  // 格式化为 datetime-local 需要的格式 (YYYY-MM-DDTHH:mm)
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  formData.value.expires_at = `${year}-${month}-${day}T${hours}:${minutes}`
}

// 清除过期时间（设置为永不过期）
const clearExpiresAt = () => {
  formData.value.expires_at = ''
}

// 检查是否有完整密钥（从 localStorage）
const hasFullKey = (id) => {
  const numKey = `api_key_${Number(id)}`
  const strKey = `api_key_${String(id)}`
  return !!(localStorage.getItem(numKey) || localStorage.getItem(strKey))
}

// 复制文本到剪贴板的辅助函数
const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    // 降级方案：使用临时输入框
    try {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)
      return success
    } catch (err) {
      console.error('复制失败:', err)
      return false
    }
  }
}

// 从列表复制密钥
const copyKeyFromList = async (id) => {
  const idNum = Number(id)
  const numKey = `api_key_${idNum}`
  const strKey = `api_key_${String(id)}`
  
  // 尝试从 localStorage 获取完整密钥
  let fullKey = localStorage.getItem(numKey) || localStorage.getItem(strKey)
  
  // 如果 localStorage 中没有，尝试通过 API 获取
  if (!fullKey) {
    try {
      const result = await apiKeysApi.getFullKey(idNum)
      if (result && result.key) {
        fullKey = result.key
        // 保存到 localStorage 以便下次使用
        localStorage.setItem(numKey, fullKey)
        localStorage.setItem(strKey, fullKey)
      } else {
        showToast('无法获取完整密钥，该密钥可能是在加密功能添加之前创建的', 'error')
        return
      }
    } catch (error) {
      console.error('获取完整密钥失败:', error)
      showToast('获取密钥失败: ' + (error.response?.data?.detail || error.message || '未知错误'), 'error')
      return
    }
  }
  
  // 确保复制的是密钥字符串，而不是 ID
  const keyToCopy = String(fullKey).trim()
  
  // 验证：如果获取到的是 ID（数字且长度短），说明存储有问题
  if (keyToCopy === String(idNum) || (keyToCopy.length < 20 && !isNaN(keyToCopy) && keyToCopy.length < 10)) {
    console.error('错误：存储的是 ID 而不是密钥', {
      id: idNum,
      storedValue: fullKey,
      keyToCopy,
      keyLength: keyToCopy.length,
      isSameAsId: keyToCopy === String(idNum)
    })
    showToast('密钥存储错误，无法复制。请重新创建密钥。', 'error')
    // 清除错误的存储
    localStorage.removeItem(numKey)
    localStorage.removeItem(strKey)
    return
  }
  
  // 验证密钥长度（API Key 应该是长字符串，至少 20 字符）
  if (keyToCopy.length < 20) {
    console.warn('警告：密钥长度异常', {
      id: idNum,
      keyLength: keyToCopy.length,
      keyPreview: keyToCopy.substring(0, 30)
    })
  }
  
  // 复制到剪贴板
  const success = await copyToClipboard(keyToCopy)
  if (success) {
    showToast('密钥已复制到剪贴板', 'success')
  } else {
    showToast('复制失败，请手动复制', 'error')
  }
}

// 提示消息
const toastMessage = ref('')
const toastType = ref('success')
let toastTimer = null

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  
  // 清除之前的定时器
  if (toastTimer) {
    clearTimeout(toastTimer)
  }
  
  // 3秒后自动关闭
  toastTimer = setTimeout(() => {
    toastMessage.value = ''
    toastTimer = null
  }, 3000)
}

const closeToast = () => {
  if (toastTimer) {
    clearTimeout(toastTimer)
    toastTimer = null
  }
  toastMessage.value = ''
}

// 编辑密钥
const editKey = (key) => {
  editingKey.value = key
  formData.value = {
    description: key.description,
    expires_at: key.expires_at ? new Date(key.expires_at).toISOString().slice(0, 16) : '',
    is_active: key.is_active
  }
  showEditDialog.value = true
}

// 删除密钥
const deleteKey = async (key) => {
  if (!confirm(`确定要删除密钥 "${key.description}" 吗？此操作不可恢复。`)) {
    return
  }
  
  try {
    await apiKeysApi.delete(key.id)
    await loadApiKeys()
    alert('删除成功')
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败: ' + error.message)
  }
}

// 保存密钥
const saveKey = async () => {
  if (!formData.value.description || !formData.value.description.trim()) {
    alert('请输入描述')
    return
  }
  
  saving.value = true
  try {
    const data = {
      description: formData.value.description.trim(),
      expires_at: formData.value.expires_at ? new Date(formData.value.expires_at).toISOString() : null
    }
    
    if (editingKey.value) {
      // 更新
      data.is_active = formData.value.is_active
      await apiKeysApi.update(editingKey.value.id, data)
      await loadApiKeys()
      closeDialog()
      alert('更新成功')
    } else {
      // 创建
      const result = await apiKeysApi.create(data)
      createdKeyData.value = result
      
      // 验证返回的数据结构
      if (!result || !result.id || !result.key) {
        console.error('创建 API Key 失败：返回数据不完整', result)
        alert('创建失败：服务器返回数据不完整')
        return
      }
      
      // 确保 key 是字符串且不是 ID
      const keyValue = String(result.key).trim()
      const idValue = Number(result.id)
      
      // 验证：密钥应该是长字符串，ID 应该是数字
      if (keyValue === String(idValue) || keyValue.length < 20) {
        console.error('错误：返回的 key 可能是 ID 而不是密钥', {
          id: idValue,
          key: keyValue,
          keyLength: keyValue.length,
          isSameAsId: keyValue === String(idValue)
        })
        alert('错误：服务器返回的数据格式不正确')
        return
      }
      
      // 保存完整密钥到 localStorage（以 ID 为 key，同时保存数字和字符串格式）
      const storageKey = `api_key_${idValue}`
      localStorage.setItem(storageKey, keyValue)
      // 同时保存字符串格式，以防万一
      localStorage.setItem(`api_key_${String(result.id)}`, keyValue)
      
      console.log('API Key 已保存到 localStorage:', {
        storageKey,
        id: idValue,
        keyLength: keyValue.length,
        keyPreview: keyValue.substring(0, 20) + '...'
      })
      closeDialog()
      showKeyDialog.value = true
      if (confirm('是否将该密钥设为全局默认 APPKey？')) {
        apiKeysStore.setDefaultKey(idValue)
        showToast('默认 APPKey 已更新', 'success')
      }
      await loadApiKeys()
    }
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

// 关闭对话框
const closeDialog = () => {
  showCreateDialog.value = false
  showEditDialog.value = false
  editingKey.value = null
  formData.value = {
    description: '',
    expires_at: '',
    is_active: true
  }
}

const createEditDialogVisible = computed(() => showCreateDialog.value || showEditDialog.value)
const closeKeyDialog = () => {
  showKeyDialog.value = false
}

useModal(createEditDialogVisible, closeDialog)
useModal(showKeyDialog, closeKeyDialog)

// 复制密钥（创建对话框中的）
const copyKey = async () => {
  if (keyInput.value && createdKeyData.value?.key) {
    keyInput.value.select()
    const success = await copyToClipboard(createdKeyData.value.key)
    if (success) {
      showToast('密钥已复制到剪贴板', 'success')
    } else {
      showToast('复制失败，请手动复制', 'error')
    }
  }
}


onMounted(() => {
  loadApiKeys()
})
</script>


