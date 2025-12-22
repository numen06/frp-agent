<template>
  <div class="page">
    <!-- 顶部导航栏 -->
    <header class="navbar navbar-expand-md d-print-none">
      <div class="container-xl">
        <button class="navbar-toggler d-md-none" type="button" data-bs-toggle="collapse" data-bs-target="#navbar-menu" aria-controls="navbar-menu" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <h1 class="navbar-brand navbar-brand-autodark">
          <router-link to="/dashboard">
            <span class="navbar-brand-icon">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0" />
                <path d="M12 7v5l3 3" />
              </svg>
            </span>
            <span class="navbar-brand-text">frp-agent</span>
          </router-link>
        </h1>
        <div class="navbar-nav flex-row order-md-last">
          <div class="nav-item d-none d-md-flex me-3">
            <a href="#" class="nav-link px-0" data-bs-toggle="dropdown" tabindex="-1" aria-label="Show notifications">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3h-16a4 4 0 0 0 2 -3v-3a7 7 0 0 1 4 -6" />
                <path d="M9 17v1a3 3 0 0 0 6 0v-1" />
              </svg>
              <span class="badge bg-red"></span>
            </a>
          </div>
          <div class="nav-item dropdown">
            <a href="#" class="nav-link d-flex lh-1 text-reset p-0" data-bs-toggle="dropdown" aria-label="Open user menu">
              <span class="avatar avatar-sm" :style="{ backgroundImage: `url(https://ui-avatars.com/api/?name=${encodeURIComponent(authStore.username || 'Admin')}&background=206bcb&color=fff)` }"></span>
              <div class="d-none d-xl-block ps-2">
                <div>{{ authStore.username || '管理员' }}</div>
                <div class="mt-0 small text-muted">管理员</div>
              </div>
            </a>
            <div class="dropdown-menu dropdown-menu-end dropdown-menu-arrow">
              <router-link to="/settings" class="dropdown-item">设置</router-link>
              <div class="dropdown-divider"></div>
              <a href="#" class="dropdown-item" @click.prevent="handleLogout">退出登录</a>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- 水平导航栏 -->
    <div class="navbar-expand-md">
      <div class="collapse navbar-collapse" id="navbar-menu">
        <div class="navbar navbar-light">
          <div class="container-xl">
            <ul class="navbar-nav">
              <li class="nav-item">
                <router-link to="/dashboard" class="nav-link" :class="{ active: $route.path === '/dashboard' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M4 4h6v8h-6z" />
                      <path d="M4 16h6v4h-6z" />
                      <path d="M14 12h6v8h-6z" />
                      <path d="M14 4h6v4h-6z" />
                    </svg>
                  </span>
                  <span class="nav-link-title">仪表板</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/servers" class="nav-link" :class="{ active: $route.path === '/servers' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M3 12a1 1 0 0 0 1 1h4.586a1 1 0 0 0 .707 -1.707l-2.586 -2.586a1 1 0 0 0 -1.414 0l-2.586 2.586a1 1 0 0 0 .707 1.707h4.586a1 1 0 0 0 1 -1z" />
                      <path d="M21 12a1 1 0 0 1 -1 1h-4.586a1 1 0 0 1 -.707 -1.707l2.586 -2.586a1 1 0 0 1 1.414 0l2.586 2.586a1 1 0 0 1 -.707 1.707h-4.586a1 1 0 0 1 -1 -1z" />
                      <path d="M12 3a1 1 0 0 1 1 1v4.586a1 1 0 0 1 -1.707 .707l-2.586 -2.586a1 1 0 0 1 0 -1.414l2.586 -2.586a1 1 0 0 1 1.707 .707v4.586a1 1 0 0 1 1 1z" />
                      <path d="M12 21a1 1 0 0 1 -1 -1v-4.586a1 1 0 0 1 1.707 -.707l2.586 2.586a1 1 0 0 1 0 1.414l-2.586 2.586a1 1 0 0 1 -1.707 -.707v-4.586a1 1 0 0 1 -1 -1z" />
                    </svg>
                  </span>
                  <span class="nav-link-title">服务器管理</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/proxies" class="nav-link" :class="{ active: $route.path === '/proxies' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M9 6l11 0" />
                      <path d="M9 12l11 0" />
                      <path d="M9 18l11 0" />
                      <path d="M5 6l0 .01" />
                      <path d="M5 12l0 .01" />
                      <path d="M5 18l0 .01" />
                    </svg>
                  </span>
                  <span class="nav-link-title">代理列表</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/groups" class="nav-link" :class="{ active: $route.path === '/groups' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M9 4h3l2 2h5a2 2 0 0 1 2 2v7a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2" />
                      <path d="M17 17v2a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2h2" />
                    </svg>
                  </span>
                  <span class="nav-link-title">分组管理</span>
                </router-link>
              </li>
              <li class="nav-item">
                <router-link to="/converter" class="nav-link" :class="{ active: $route.path === '/converter' }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                      <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
                    </svg>
                  </span>
                  <span class="nav-link-title">INI 转换</span>
                </router-link>
              </li>
              <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown" :class="{ active: $route.path.startsWith('/settings') }">
                  <span class="nav-link-icon d-md-none d-lg-inline-block">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z" />
                      <path d="M9 12a3 3 0 1 0 6 0a3 3 0 0 0 -6 0" />
                    </svg>
                  </span>
                  <span class="nav-link-title">设置</span>
                </a>
                <div class="dropdown-menu">
                  <router-link to="/settings" class="dropdown-item">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z" />
                      <path d="M9 12a3 3 0 1 0 6 0a3 3 0 0 0 -6 0" />
                    </svg>
                    用户设置
                  </router-link>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="page-wrapper">
      <div class="page-header d-print-none">
        <div class="container-xl">
          <div class="row g-2 align-items-center">
            <div class="col">
              <div class="page-pretitle">{{ pagePretitle }}</div>
              <h2 class="page-title">{{ pageTitle }}</h2>
            </div>
          </div>
        </div>
      </div>

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
                <li class="list-inline-item">frp-agent v1.0</li>
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
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const pagePretitle = computed(() => {
  if (route.path === '/dashboard') return 'OVERVIEW'
  if (route.path === '/servers') return 'MANAGEMENT'
  if (route.path === '/settings') return 'SETTINGS'
  return ''
})

const pageTitle = computed(() => {
  if (route.path === '/dashboard') return 'Dashboard'
  if (route.path === '/servers') return '服务器管理'
  if (route.path === '/settings') return 'Settings'
  return 'frp-agent'
})

const handleLogout = async () => {
  if (confirm('确定要退出登录吗？')) {
    authStore.logout()
    router.push('/login')
  }
}
</script>

