<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      @click.self="close"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close" />
      <div
        class="relative z-10 flex max-h-[min(92vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between border-b border-gray-200 px-5 py-3.5">
          <h2 class="text-lg font-semibold text-gray-900">客户端升级</h2>
          <button type="button" class="rounded-lg p-2 text-gray-500 hover:bg-gray-100" aria-label="关闭" @click="close">×</button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
          <div v-if="proxy" class="mb-3 rounded-lg bg-gray-50 p-3 text-gray-700">
            <div><span class="text-gray-500">代理：</span>{{ proxy.name }}</div>
            <div><span class="text-gray-500">SSH：</span>{{ sshHint }}</div>
          </div>

          <SshCredentialForm v-model="credentialId" />

          <div class="mt-3">
            <label class="mb-1 block text-xs font-medium text-gray-600">frpc 安装路径</label>
            <input v-model="installPath" type="text" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm" />
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              :disabled="!credentialId || scanning"
              @click="runScan"
            >
              {{ scanning ? '扫描中...' : '扫描' }}
            </button>
            <button
              type="button"
              class="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
              :disabled="!canUpgrade || upgrading"
              @click="runUpgrade"
            >
              {{ upgrading ? '升级中...' : '执行升级' }}
            </button>
          </div>

          <div v-if="scanState" class="mt-4 rounded-lg border border-gray-200 p-3">
            <div class="mb-1 font-medium text-gray-900">
              状态：
              <span :class="statusClass">{{ statusLabel }}</span>
            </div>
            <div v-if="scanState.current_version" class="text-gray-600">当前版本：{{ scanState.current_version }}</div>
            <div v-if="scanState.target_version" class="text-gray-600">目标版本：{{ scanState.target_version }}</div>
            <div v-if="scanState.platform" class="text-gray-600">平台：{{ scanState.platform }}</div>
            <div v-if="scanState.message" class="mt-1 text-gray-500">{{ scanState.message }}</div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import SshCredentialForm from '@/components/SshCredentialForm.vue'
import { clientUpgradeApi } from '@/api/clientUpgrade'
import { isSshCandidateProxy } from '@/utils/sshCandidate'

const props = defineProps({
  modelValue: Boolean,
  proxy: { type: Object, default: null },
  server: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'upgraded'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const credentialId = ref(0)
const installPath = ref('/opt/frp')
const scanning = ref(false)
const upgrading = ref(false)
const scanState = ref(null)

const sshHint = computed(() => {
  if (!props.proxy || !props.server) return '-'
  const port = props.proxy.remote_port
  return port ? `${props.server.server_addr}:${port}` : '-'
})

const canUpgrade = computed(() => scanState.value?.upgradeable === true)

const STATUS_LABELS = {
  upgradeable: '可升级',
  latest: '已最新',
  unreachable: '不可达',
  auth_failed: '认证失败',
  permission_denied: '权限不足',
  not_ssh: '非 SSH',
  unsupported_platform: '不支持的平台',
  no_package: '无安装包',
  upgraded: '已升级',
  upgrade_failed: '升级失败',
  unknown: '未知'
}

const statusLabel = computed(() => STATUS_LABELS[scanState.value?.status] || scanState.value?.status || '-')

const statusClass = computed(() => {
  const s = scanState.value?.status
  if (s === 'upgradeable') return 'text-green-700'
  if (s === 'latest' || s === 'upgraded') return 'text-blue-700'
  if (s === 'not_ssh') return 'text-gray-600'
  return 'text-amber-700'
})

watch(visible, (v) => {
  if (v) {
    scanState.value = null
    installPath.value = '/opt/frp'
  }
})

function close() {
  visible.value = false
}

async function runScan() {
  if (!props.proxy?.id || !credentialId.value) return
  scanning.value = true
  try {
    scanState.value = await clientUpgradeApi.scanProxy(props.proxy.id, {
      credential_id: credentialId.value,
      install_path: installPath.value
    })
  } catch (e) {
    alert(e.message || '扫描失败')
  } finally {
    scanning.value = false
  }
}

async function runUpgrade() {
  if (!props.proxy?.id || !credentialId.value) return
  if (!confirm('确认升级该主机上的 frpc 二进制？')) return
  upgrading.value = true
  try {
    const result = await clientUpgradeApi.upgradeProxy(props.proxy.id, {
      credential_id: credentialId.value,
      install_path: installPath.value
    })
    if (result.success) {
      scanState.value = { ...scanState.value, status: 'upgraded', message: result.message, current_version: result.current_version }
      emit('upgraded')
    } else {
      scanState.value = { ...scanState.value, status: result.status, message: result.message, upgradeable: false }
      alert(result.message || '升级失败')
    }
  } catch (e) {
    alert(e.message || '升级失败')
  } finally {
    upgrading.value = false
  }
}

defineExpose({ isSshCandidateProxy })
</script>
