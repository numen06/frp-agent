<template>
  <div>
    <div class="row">
      <div class="col-lg-8 offset-lg-2">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">用户设置</h3>
          </div>
          <div class="card-body">
            <!-- 账号信息 -->
            <div class="card mb-3">
              <div class="card-header">
                <h3 class="card-title">账号信息</h3>
              </div>
              <div class="card-body">
                <div class="row">
                  <div class="col-md-6">
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { settingsApi } from '@/api/settings'

const router = useRouter()
const authStore = useAuthStore()

const userSettings = reactive({
  username: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

onMounted(async () => {
  await loadUserSettings()
})

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
    
    alert('密码修改成功，3秒后跳转到登录页')
    
    setTimeout(() => {
      authStore.logout()
      router.push('/login')
    }, 3000)
  } catch (error) {
    alert('修改失败: ' + error.message)
  }
}
</script>

