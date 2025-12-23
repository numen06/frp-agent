<template>
  <div>
    <!-- 欢迎区域 -->
    <div class="card">
      <div class="card-body">
        <h3 class="card-title mb-0">欢迎回来，{{ authStore.username || '管理员' }}</h3>
        <div class="text-muted">共 {{ serversStore.servers.length }} 个服务器</div>
      </div>
    </div>

    <!-- 汇总统计卡片 -->
    <div class="card mt-3 mb-3">
      <div class="card-header">
        <h3 class="card-title">汇总统计</h3>
      </div>
      <div class="card-body">
        <div class="row">
          <div class="col-sm-6 col-lg-3">
                <div class="d-flex align-items-center mb-3">
                  <div class="subheader">代理总数</div>
                  <div class="ms-auto lh-1">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M9 6l11 0" />
                      <path d="M9 12l11 0" />
                      <path d="M9 18l11 0" />
                      <path d="M5 6l0 .01" />
                      <path d="M5 12l0 .01" />
                      <path d="M5 18l0 .01" />
                    </svg>
                  </div>
                </div>
                <div class="h1 mb-0">{{ totalStats.total }}</div>
          </div>
          <div class="col-sm-6 col-lg-3">
                <div class="d-flex align-items-center mb-3">
                  <div class="subheader">在线代理</div>
                  <div class="ms-auto lh-1">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
                      <path d="M12 8l0 4" />
                      <path d="M12 16l.01 0" />
                    </svg>
                  </div>
                </div>
                <div class="h1 mb-0">{{ totalStats.online }}</div>
                <div class="text-muted small">在线率: {{ totalOnlineRate }}%</div>
          </div>
          <div class="col-sm-6 col-lg-3">
                <div class="d-flex align-items-center mb-3">
                  <div class="subheader">离线代理</div>
                  <div class="ms-auto lh-1">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
                      <path d="M12 8l0 4" />
                      <path d="M12 16l.01 0" />
                    </svg>
                  </div>
                </div>
                <div class="h1 mb-0">{{ totalStats.offline }}</div>
                <div class="text-muted small">离线率: {{ totalOfflineRate }}%</div>
          </div>
          <div class="col-sm-6 col-lg-3">
                <div class="d-flex align-items-center mb-3">
                  <div class="subheader">端口分配</div>
                  <div class="ms-auto lh-1">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
                      <path d="M12 6l0 6l6 -6" />
                    </svg>
                  </div>
                </div>
                <div class="h1 mb-0">{{ totalStats.portCount }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 各服务器统计 -->
    <div class="card mt-3 mb-3" v-if="serversStore.servers.length > 0">
      <div class="card-header">
        <h3 class="card-title">服务器详情</h3>
      </div>
      <div v-if="loading" class="card-body">
        <div class="text-center py-4">
          <div class="spinner-border spinner-border-sm" role="status"></div>
          <span class="ms-2">加载中...</span>
        </div>
      </div>
      <div v-else class="table-responsive">
        <table class="table table-vcenter card-table table-striped w-100">
          <thead>
            <tr>
              <th>服务器名称</th>
              <th>服务器地址</th>
              <th>连接状态</th>
              <th>代理总数</th>
              <th>在线</th>
              <th>离线</th>
              <th>端口数</th>
              <th>在线率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="server in serversStore.servers" :key="server.id">
              <td>
                <div class="fw-bold">{{ server.name }}</div>
                <div class="text-muted small">{{ server.api_base_url }}</div>
              </td>
              <td>
                <div>{{ server.server_addr }}:{{ server.server_port }}</div>
                <div class="text-muted small">{{ server.auth_username }}</div>
              </td>
              <td>
                <span class="badge" :class="getServerStatusBadgeClass(server)">
                  {{ getServerStatusText(server) }}
                </span>
              </td>
              <td>
                <div class="fw-bold">{{ getServerStats(server.id).total }}</div>
              </td>
              <td>
                <span class="badge text-bg-success">
                  {{ getServerStats(server.id).online }}
                </span>
              </td>
              <td>
                <span class="badge text-bg-danger">
                  {{ getServerStats(server.id).offline }}
                </span>
              </td>
              <td>{{ getServerStats(server.id).portCount }}</td>
              <td>
                <div class="d-flex align-items-center">
                  <div class="progress progress-sm me-2" style="width: 60px;">
                    <div class="progress-bar" :class="getServerOnlineRate(server.id) > 0 ? 'bg-success' : 'bg-secondary'" 
                         :style="`width: ${getServerOnlineRate(server.id)}%`" 
                         role="progressbar"
                         :aria-valuenow="getServerOnlineRate(server.id)"
                         aria-valuemin="0"
                         aria-valuemax="100"></div>
                  </div>
                  <span class="small">{{ getServerOnlineRate(server.id) }}%</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 快速操作 -->
    <div class="card mt-3">
      <div class="card-header">
        <h3 class="card-title">快速操作</h3>
      </div>
      <div class="card-body">
        <div class="row g-2">
          <div class="col-6 col-md-3">
            <router-link to="/proxies" class="btn btn-outline-primary w-100">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon me-1" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M9 6l11 0" />
                <path d="M9 12l11 0" />
                <path d="M9 18l11 0" />
                <path d="M5 6l0 .01" />
                <path d="M5 12l0 .01" />
                <path d="M5 18l0 .01" />
              </svg>
              代理列表
            </router-link>
          </div>
          <div class="col-6 col-md-3">
            <router-link to="/groups" class="btn btn-outline-primary w-100">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon me-1" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M9 4h3l2 2h5a2 2 0 0 1 2 2v7a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2" />
                <path d="M17 17v2a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2h2" />
              </svg>
              分组管理
            </router-link>
          </div>
          <div class="col-6 col-md-3">
            <router-link to="/converter" class="btn btn-outline-primary w-100">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon me-1" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
              </svg>
              INI 转换
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useServersStore } from '@/stores/servers'
import { proxyApi } from '@/api/proxies'
import { useRefresh } from '@/composables/useRefresh'

const authStore = useAuthStore()
const serversStore = useServersStore()
const { refreshEvent } = useRefresh()

const loading = ref(false)
const serverStatsMap = ref(new Map()) // 存储每个服务器的统计数据

// 汇总统计
const totalStats = computed(() => {
  let total = 0
  let online = 0
  let offline = 0
  const ports = new Set()
  
  serverStatsMap.value.forEach((stats) => {
    total += stats.total
    online += stats.online
    offline += stats.offline
    stats.ports.forEach(port => ports.add(port))
  })
  
  return {
    total,
    online,
    offline,
    portCount: ports.size
  }
})

const totalOnlineRate = computed(() => {
  if (totalStats.value.total === 0) return 0
  return Math.round((totalStats.value.online / totalStats.value.total) * 100)
})

const totalOfflineRate = computed(() => {
  if (totalStats.value.total === 0) return 0
  return Math.round((totalStats.value.offline / totalStats.value.total) * 100)
})

// 获取指定服务器的统计数据
const getServerStats = (serverId) => {
  return serverStatsMap.value.get(serverId) || {
    total: 0,
    online: 0,
    offline: 0,
    portCount: 0,
    ports: new Set()
  }
}

// 获取指定服务器的在线率
const getServerOnlineRate = (serverId) => {
  const stats = getServerStats(serverId)
  if (stats.total === 0) return 0
  return Math.round((stats.online / stats.total) * 100)
}

// 加载所有服务器的数据
const loadAllServersData = async () => {
  if (serversStore.servers.length === 0) return
  
  loading.value = true
  try {
    // 并行加载所有服务器的代理数据
    const promises = serversStore.servers.map(async (server) => {
      try {
        const response = await proxyApi.getProxies({
          frps_server_id: server.id,
          sync_from_frps: false,
          page: 1,
          page_size: 1000 // 获取足够多的数据用于统计
        })
        
        // 处理分页响应格式
        const proxies = response.items || response.proxies || []
        const stats = {
          total: response.total || proxies.length,
          online: proxies.filter(p => p.status === 'online').length,
          offline: proxies.filter(p => p.status === 'offline').length,
          ports: new Set()
        }
        
        proxies.forEach(p => {
          if (p.remote_port) stats.ports.add(p.remote_port)
        })
        
        stats.portCount = stats.ports.size
        
        serverStatsMap.value.set(server.id, stats)
      } catch (error) {
        console.error(`加载服务器 ${server.name} 的数据失败:`, error)
        // 设置默认值
        serverStatsMap.value.set(server.id, {
          total: 0,
          online: 0,
          offline: 0,
          portCount: 0,
          ports: new Set()
        })
      }
    })
    
    await Promise.all(promises)
  } catch (error) {
    console.error('加载服务器数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 监听刷新事件，当同步操作完成后自动刷新统计数据
watch(refreshEvent, () => {
  if (refreshEvent.value > 0) {
    loadAllServersData()
  }
})

onMounted(async () => {
  try {
    await serversStore.loadServers()
    await loadAllServersData()
  } catch (error) {
    console.error('初始化失败:', error)
  }
})

const getServerStatusBadgeClass = (server) => {
  if (!server.last_test_status || server.last_test_status === 'unknown') return 'text-bg-secondary'
  return server.last_test_status === 'online' ? 'text-bg-success' : 'text-bg-danger'
}

const getServerStatusText = (server) => {
  if (!server.last_test_status || server.last_test_status === 'unknown') return '未测试'
  return server.last_test_status === 'online' ? '在线' : '离线'
}
</script>
