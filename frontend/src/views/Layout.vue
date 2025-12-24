<template>
  <div class="page">
    <!-- 顶部导航栏 -->
    <header class="navbar navbar-expand-md d-print-none">
      <div class="container-xl">
        <button class="navbar-toggler d-md-none" type="button" @click="navCollapse.toggle()" :aria-expanded="navCollapse.isOpen.value" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <h1 class="navbar-brand navbar-brand-autodark">
          <router-link to="/dashboard" class="navbar-brand">
            <span class="navbar-brand-icon me-2">
              <FrpLogo :size="28" color="#206bcb" />
            </span>
            <span class="navbar-brand-text">
              <span class="text-primary fw-bold">FRP</span>
              <span class="text-muted fw-medium">-AGENT</span>
            </span>
          </router-link>
        </h1>
        <div class="navbar-nav flex-row order-md-last">
          <div class="nav-item d-none d-md-flex me-3">
            <a href="#" class="nav-link px-0" tabindex="-1" aria-label="Show notifications">
              <IconBell class="icon" />
              <span class="badge bg-red"></span>
            </a>
          </div>
          <div class="nav-item dropdown">
            <a 
              ref="userDropdown.triggerRef" 
              href="#" 
              class="nav-link d-flex lh-1 text-reset p-0" 
              @click.prevent="userDropdown.toggle()"
              aria-label="Open user menu"
            >
              <span class="avatar avatar-sm" :style="{ backgroundImage: `url(https://ui-avatars.com/api/?name=${encodeURIComponent(authStore.username || 'Admin')}&background=206bcb&color=fff)` }"></span>
              <div class="d-none d-xl-block ps-2">
                <div>{{ authStore.username || '管理员' }}</div>
                <div class="mt-0 small text-muted">管理员</div>
              </div>
            </a>
            <div 
              ref="userDropdown.dropdownRef"
              class="dropdown-menu dropdown-menu-end dropdown-menu-arrow"
              :class="{ show: userDropdown.isOpen.value }"
              @click.stop
            >
              <a href="#" class="dropdown-item" @click.prevent="handleUserManage(); userDropdown.close()">
                <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0" />
                  <path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2" />
                </svg>
                用户管理
              </a>
              <div class="dropdown-divider"></div>
              <a href="#" class="dropdown-item" @click.prevent="handleLogout(); userDropdown.close()">
                <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M14 8v-2a2 2 0 0 0 -2 -2h-7a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h7a2 2 0 0 0 2 -2v-2" />
                  <path d="M7 12h14l-3 -3m0 6l3 -3" />
                </svg>
                退出登录
              </a>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- 水平导航栏 -->
    <div class="navbar-expand-md">
      <div class="collapse navbar-collapse" :class="{ show: navCollapse.isOpen.value }" id="navbar-menu">
        <div class="navbar navbar-light">
          <div class="container-xl">
            <ul class="navbar-nav">
              <li class="nav-item">
                <router-link to="/dashboard" class="nav-link" :class="{ active: $route.path === '/dashboard' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <IconLayoutDashboard class="icon" />
                  </span>
                  <span class="nav-link-title">仪表板</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/proxies" class="nav-link" :class="{ active: $route.path === '/proxies' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <IconList class="icon" />
                  </span>
                  <span class="nav-link-title">代理列表</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/groups" class="nav-link" :class="{ active: $route.path === '/groups' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <IconFolder class="icon" />
                  </span>
                  <span class="nav-link-title">分组管理</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/converter" class="nav-link" :class="{ active: $route.path === '/converter' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <IconRefresh class="icon" />
                  </span>
                  <span class="nav-link-title">INI 转换</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/servers" class="nav-link" :class="{ active: $route.path === '/servers' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <IconServer class="icon" />
                  </span>
                  <span class="nav-link-title">服务器管理</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/api-keys" class="nav-link" :class="{ active: $route.path === '/api-keys' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <IconKey class="icon" />
                  </span>
                  <span class="nav-link-title">密钥管理</span>
                </router-link>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="page-wrapper">
      <div class="page-body">
        <div class="container-xl">
          <router-view />
        </div>
      </div>

      <footer class="footer footer-transparent d-print-none">
        <div class="container-xl">
          <div class="row text-center align-items-center flex-row-reverse">
            <div class="col-lg-auto ms-lg-auto">
              <ul class="list-inline list-inline-dots mb-0">
                <li class="list-inline-item">FRP-AGENT v1.0</li>
              </ul>
            </div>
            <div class="col-12 col-lg-auto mt-3 mt-lg-0">
              <ul class="list-inline list-inline-dots mb-0">
                <li class="list-inline-item">Copyright &copy; 2025</li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>

    <!-- 用户管理对话框 -->
    <UserManageDialog 
      v-model:show="showUserManageDialog" 
      :force-mode="forcePasswordChange"
      :force-reason="forcePasswordChangeReason"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { IconBell, IconLayoutDashboard, IconList, IconFolder, IconRefresh, IconServer, IconKey } from '@tabler/icons-vue'
import { useAuthStore } from '@/stores/auth'
import FrpLogo from '@/components/FrpLogo.vue'
import UserManageDialog from '@/components/UserManageDialog.vue'
import { settingsApi } from '@/api/settings'
import { useDropdown } from '@/composables/useDropdown'
import { useCollapse } from '@/composables/useCollapse'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const showUserManageDialog = ref(false)
const forcePasswordChange = ref(false)
const forcePasswordChangeReason = ref('')

// 下拉菜单和折叠功能
const userDropdown = useDropdown()
const navCollapse = useCollapse()

// 检查是否需要强制修改密码
const checkPasswordRequirement = async () => {
  if (!authStore.isAuthenticated) return
  
  try {
    const result = await settingsApi.checkPasswordRequirement()
    if (result?.require_password_change) {
      forcePasswordChange.value = true
      forcePasswordChangeReason.value = result.reason || '检测到使用默认密码，请立即修改'
      showUserManageDialog.value = true
    }
  } catch (error) {
    console.warn('检查密码要求失败:', error)
  }
}

// 监听路由查询参数
watch(() => route.query, (newQuery) => {
  if (newQuery.forcePasswordChange === 'true') {
    forcePasswordChange.value = true
    forcePasswordChangeReason.value = newQuery.reason || '检测到使用默认密码，请立即修改'
    showUserManageDialog.value = true
  }
}, { immediate: true })

// 组件挂载时检查
onMounted(() => {
  if (route.query.forcePasswordChange === 'true') {
    checkPasswordRequirement()
  }
})

const handleUserManage = () => {
  showUserManageDialog.value = true
}

const handleLogout = async () => {
  if (confirm('确定要退出登录吗？')) {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
/* 确保导航栏下拉菜单不被裁剪 */
.navbar {
  overflow: visible;
}

.navbar .container-xl {
  overflow: visible;
  position: relative;
}

.navbar-nav {
  overflow: visible;
}

.navbar-nav .nav-item.dropdown {
  position: relative;
}

.navbar-nav .dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  left: auto;
  z-index: 1050;
  margin-top: 0.5rem;
  min-width: 10rem;
}

/* 确保下拉菜单在页面边缘时也能正确显示 */
@media (max-width: 768px) {
  .navbar-nav .dropdown-menu {
    right: auto;
    left: 0;
  }
}
</style>


