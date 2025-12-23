<template>
  <div class="page-body">
    <div class="container-xl">
      <div class="row">
        <div class="col-12">
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">API Key 管理</h3>
              <div class="card-actions">
                <button class="btn btn-primary" @click="showCreateDialog = true">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M12 5l0 14" />
                    <path d="M5 12l14 0" />
                  </svg>
                  创建密钥
                </button>
              </div>
            </div>
            <div class="card-body">
              <div class="table-responsive">
                <table class="table table-vcenter card-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>密钥</th>
                      <th>描述</th>
                      <th>过期时间</th>
                      <th>状态</th>
                      <th>创建时间</th>
                      <th>最后使用</th>
                      <th class="w-1">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="loading">
                      <td colspan="8" class="text-center py-4">
                        <div class="spinner-border spinner-border-sm" role="status">
                          <span class="visually-hidden">加载中...</span>
                        </div>
                      </td>
                    </tr>
                    <tr v-else-if="apiKeys.length === 0">
                      <td colspan="8" class="text-center text-muted py-4">
                        暂无 API Key，点击上方按钮创建
                      </td>
                    </tr>
                     <tr v-else v-for="key in apiKeys" :key="key.id">
                       <td>{{ key.id }}</td>
                       <td>
                         <div class="d-flex align-items-center gap-2">
                           <code class="text-muted flex-grow-1">{{ key.key }}</code>
                           <button 
                             class="btn btn-sm btn-icon"
                             :class="hasFullKey(key.id) ? 'btn-outline-primary' : 'btn-outline-secondary'"
                             @click="copyKeyFromList(key.id)"
                             :title="hasFullKey(key.id) ? '点击复制完整密钥' : '密钥已不可见，无法复制'"
                             :disabled="!hasFullKey(key.id)"
                           >
                             <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                               <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                               <path d="M7 7m0 2.667a2.667 2.667 0 0 1 2.667 -2.667h8.666a2.667 2.667 0 0 1 2.667 2.667v8.666a2.667 2.667 0 0 1 -2.667 2.667h-8.666a2.667 2.667 0 0 1 -2.667 -2.667z" />
                               <path d="M4.012 16.737a2.005 2.005 0 0 1 -1.012 -1.737v-10c0 -1.1 .9 -2 2 -2h10c.75 0 1.158 .385 1.5 1" />
                             </svg>
                           </button>
                         </div>
                       </td>
                       <td>{{ key.description }}</td>
                      <td>
                        <span v-if="key.expires_at">
                          {{ formatDateTime(key.expires_at) }}
                        </span>
                        <span v-else class="text-muted">永不过期</span>
                      </td>
                      <td>
                        <span v-if="key.is_expired" class="badge bg-red">已过期</span>
                        <span v-else-if="!key.is_active" class="badge bg-secondary">已禁用</span>
                        <span v-else class="badge bg-success">正常</span>
                      </td>
                      <td>{{ formatDateTime(key.created_at) }}</td>
                      <td>
                        <span v-if="key.last_used_at">{{ formatDateTime(key.last_used_at) }}</span>
                        <span v-else class="text-muted">从未使用</span>
                      </td>
                      <td>
                        <div class="btn-list flex-nowrap">
                          <button 
                            class="btn btn-sm btn-outline-primary" 
                            @click="editKey(key)"
                            :disabled="key.is_expired"
                          >
                            编辑
                          </button>
                          <button 
                            class="btn btn-sm btn-outline-danger" 
                            @click="deleteKey(key)"
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <div class="modal modal-blur fade" :class="{ show: showCreateDialog || showEditDialog }" :style="{ display: (showCreateDialog || showEditDialog) ? 'block' : 'none' }" tabindex="-1" role="dialog">
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
                  class="btn btn-sm btn-outline-secondary"
                  @click="setExpiresDays(7)"
                  title="7天后过期"
                >
                  7天
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-secondary"
                  @click="setExpiresDays(30)"
                  title="30天后过期"
                >
                  30天
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-secondary"
                  @click="setExpiresDays(90)"
                  title="90天后过期"
                >
                  90天
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-secondary"
                  @click="setExpiresDays(180)"
                  title="180天后过期"
                >
                  180天
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-secondary"
                  @click="setExpiresDays(365)"
                  title="1年后过期"
                >
                  1年
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-secondary"
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
            <button type="button" class="btn btn-secondary" @click="closeDialog">取消</button>
            <button type="button" class="btn btn-primary" @click="saveKey" :disabled="!formData.description || saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showCreateDialog || showEditDialog" class="modal-backdrop fade show" @click="closeDialog"></div>

    <!-- 创建成功对话框（显示完整密钥） -->
    <div class="modal modal-blur fade" :class="{ show: showKeyDialog }" :style="{ display: showKeyDialog ? 'block' : 'none' }" tabindex="-1" role="dialog">
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
                  class="btn btn-outline-secondary" 
                  type="button"
                  @click="copyKey"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M7 7m0 2.667a2.667 2.667 0 0 1 2.667 -2.667h8.666a2.667 2.667 0 0 1 2.667 2.667v8.666a2.667 2.667 0 0 1 -2.667 2.667h-8.666a2.667 2.667 0 0 1 -2.667 -2.667z" />
                    <path d="M4.012 16.737a2.005 2.005 0 0 1 -1.012 -1.737v-10c0 -1.1 .9 -2 2 -2h10c.75 0 1.158 .385 1.5 1" />
                  </svg>
                  复制
                </button>
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label">使用方式</label>
              <div class="card">
                <div class="card-body">
                  <code class="text-muted">
                    Authorization: Bearer {{ createdKeyData?.key }}
                  </code>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-primary" @click="showKeyDialog = false">我已保存</button>
          </div>
        </div>
      </div>
     </div>
     <div v-if="showKeyDialog" class="modal-backdrop fade show" @click="showKeyDialog = false"></div>

     <!-- 提示消息 -->
     <div v-if="toastMessage" class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 9999;">
       <div class="toast show" :class="toastType === 'success' ? 'bg-success' : 'bg-danger'" role="alert">
         <div class="toast-body text-white">
           {{ toastMessage }}
         </div>
       </div>
     </div>
   </div>
 </template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiKeysApi } from '@/api/apiKeys'

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
    const data = await apiKeysApi.list()
    apiKeys.value = data || []
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

// 从列表复制密钥
const copyKeyFromList = async (id) => {
  const idNum = Number(id)
  const numKey = `api_key_${idNum}`
  const strKey = `api_key_${String(id)}`
  
  // 尝试从 localStorage 获取完整密钥
  let fullKey = localStorage.getItem(numKey) || localStorage.getItem(strKey)
  
  if (!fullKey) {
    showToast('密钥已不可见，无法复制。如需使用，请重新创建密钥。', 'error')
    return
  }
  
  // 确保复制的是密钥字符串，而不是 ID
  const keyToCopy = String(fullKey).trim()
  
  // 验证：如果获取到的是 ID（数字且长度短），说明存储有问题
  if (keyToCopy === String(idNum) || (keyToCopy.length < 20 && !isNaN(keyToCopy) && keyToCopy.length < 10)) {
    console.error('错误：localStorage 中存储的是 ID 而不是密钥', {
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
  
  try {
    await navigator.clipboard.writeText(keyToCopy)
    showToast('密钥已复制到剪贴板', 'success')
  } catch (error) {
    // 降级方案：使用临时输入框
    try {
      const textarea = document.createElement('textarea')
      textarea.value = keyToCopy
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)
      
      if (success) {
        showToast('密钥已复制到剪贴板', 'success')
      } else {
        throw new Error('execCommand 失败')
      }
    } catch (err) {
      console.error('复制失败:', err)
      showToast('复制失败，请手动复制', 'error')
    }
  }
}

// 提示消息
const toastMessage = ref('')
const toastType = ref('success')
const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
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

// 复制密钥（创建对话框中的）
const copyKey = async () => {
  if (keyInput.value && createdKeyData.value?.key) {
    keyInput.value.select()
    try {
      await navigator.clipboard.writeText(createdKeyData.value.key)
      showToast('密钥已复制到剪贴板', 'success')
    } catch (error) {
      // 降级方案
      try {
        document.execCommand('copy')
        showToast('密钥已复制到剪贴板', 'success')
      } catch (err) {
        showToast('复制失败，请手动复制', 'error')
      }
    }
  }
}

onMounted(() => {
  loadApiKeys()
})
</script>

<style scoped>
.required::after {
  content: ' *';
  color: red;
}

.form-hint {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: #6c757d;
}

.font-monospace {
  font-family: 'Courier New', Courier, monospace;
}

.gap-1 {
  gap: 0.25rem;
}

.gap-2 {
  gap: 0.5rem;
}

.btn-icon {
  padding: 0.25rem 0.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toast-container {
  animation: slideInRight 0.3s ease-out;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@media (max-width: 576px) {
  .d-flex.flex-wrap {
    flex-direction: column;
  }
  
  .d-flex.flex-wrap .btn {
    width: 100%;
  }
}
</style>

