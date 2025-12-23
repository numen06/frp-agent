<template>
  <div v-if="show" class="modal-backdrop fade show" @click="!forceMode && close()"></div>
  <div class="modal modal-blur fade" :class="{ show: show, 'd-block': show }" tabindex="-1" role="dialog" :style="show ? 'display: block;' : ''" @click.self="!forceMode && close()">
    <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ forceMode ? '强制修改密码' : '用户管理' }}</h5>
          <button v-if="!forceMode" type="button" class="btn-close" @click="close"></button>
        </div>
        <div class="modal-body">
          <!-- 强制修改密码提示 -->
          <div v-if="forceMode" class="alert alert-danger mb-3" role="alert">
            <h4 class="alert-title">安全提示</h4>
            <div>{{ forceReason || '检测到您使用的是默认密码，为了账户安全，请立即修改密码。修改完成后才能继续使用系统。' }}</div>
          </div>

          <!-- 账号信息 -->
          <div v-if="!forceMode" class="card mb-3">
            <div class="card-header">
              <h3 class="card-title">账号信息</h3>
            </div>
            <div class="card-body">
              <div class="row">
                <div class="col-md-12">
                  <div class="text-muted">用户名</div>
                  <div class="fw-bold">{{ userSettings.username }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 修改密码 -->
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">修改密码</h3>
            </div>
            <div class="card-body">
              <form @submit.prevent="handleChangePassword">
                <div class="mb-3">
                  <label class="form-label">当前密码 <span class="text-danger">*</span></label>
                  <input type="password" class="form-control" v-model="passwordForm.old_password" required />
                </div>
                
                <div class="mb-3">
                  <label class="form-label">新密码 <span class="text-danger">*</span></label>
                  <input type="password" class="form-control" v-model="passwordForm.new_password" required minlength="6" />
                  <small class="form-hint">密码长度至少 6 位</small>
                </div>
                
                <div class="mb-3">
                  <label class="form-label">确认新密码 <span class="text-danger">*</span></label>
                  <input type="password" class="form-control" v-model="passwordForm.confirm_password" required />
                </div>
                
                <div class="form-footer">
                  <button v-if="!forceMode" type="button" class="btn btn-secondary me-auto" @click="close">取消</button>
                  <button type="submit" class="btn btn-primary">保存修改</button>
                </div>
              </form>
            </div>
          </div>

          <!-- 注意事项 -->
          <div class="alert alert-warning mt-3" role="alert">
            <h4 class="alert-title">注意事项</h4>
            <div class="text-muted">
              <ul class="mb-0">
                <li>修改密码后需要重新登录</li>
                <li>请妥善保管新密码，避免泄露</li>
                <li>建议使用强密码（包含字母、数字和特殊字符）</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { settingsApi } from '@/api/settings'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  forceMode: {
    type: Boolean,
    default: false
  },
  forceReason: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:show'])

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const userSettings = reactive({
  username: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// 监听 show 变化，加载用户设置
watch(() => props.show, async (newVal) => {
  if (newVal) {
    await loadUserSettings()
    // 重置表单
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  }
})

// 监听路由变化，检查是否需要强制修改密码
watch(() => route.query, async (newQuery) => {
  if (newQuery.forcePasswordChange === 'true' && !props.show) {
    emit('update:show', true)
  }
}, { immediate: true })

const loadUserSettings = async () => {
  try {
    const settings = await settingsApi.getUserSettings()
    userSettings.username = settings.username || authStore.username
  } catch (error) {
    alert('加载用户设置失败: ' + error.message)
  }
}

const handleChangePassword = async () => {
  if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    alert('请填写所有字段')
    return
  }
  
  if (passwordForm.new_password.length < 6) {
    alert('新密码长度至少 6 位')
    return
  }
  
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    alert('两次输入的新密码不一致')
    return
  }
  
  try {
    await settingsApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    
    if (props.forceMode) {
      alert('密码修改成功！请重新登录')
      // 清除强制修改密码的查询参数
      router.replace({ query: {} })
    } else {
      alert('密码修改成功，3秒后跳转到登录页')
    }
    
    setTimeout(() => {
      authStore.logout()
      router.push('/login')
    }, props.forceMode ? 1000 : 3000)
  } catch (error) {
    alert('修改失败: ' + error.message)
  }
}

const close = () => {
  if (!props.forceMode) {
    emit('update:show', false)
  }
}

// 使用统一的模态框功能，在强制模式下禁用ESC退出
// 将props.show转换为ref以适配useModal
const showRef = computed(() => props.show)
useModal(showRef, close, {
  disabled: computed(() => props.forceMode)
})
</script>

