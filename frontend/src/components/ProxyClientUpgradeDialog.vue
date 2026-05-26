<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      @click.self="close"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close" />
      <div
        class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl sm:h-auto sm:max-h-[min(92vh,720px)] sm:rounded-xl"
        @click.stop
      >
        <div class="sticky top-0 z-10 flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-3.5 sm:px-5">
          <h2 class="text-lg font-semibold text-gray-900">客户端升级</h2>
          <button
            type="button"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
            aria-label="关闭"
            @click="close"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 text-sm sm:px-5">
          <div v-if="proxy" class="mb-3 rounded-lg bg-gray-50 p-3 text-gray-700">
            <div class="break-all"><span class="text-gray-500">代理：</span>{{ proxy.name }}</div>
            <div class="break-all"><span class="text-gray-500">SSH：</span>{{ sshHint }}</div>
          </div>

          <SshCredentialForm v-model="credentialId" />

          <div class="mt-3">
            <label class="mb-1 block text-xs font-medium text-gray-600">frpc 安装路径</label>
            <input v-model="installPath" type="text" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm" />
          </div>

          <div class="mt-3 space-y-2">
            <label class="block text-xs font-medium text-gray-600">验证模式</label>
            <select v-model="verifyMode" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm">
              <option value="agent_callback">回调验证（推荐）</option>
              <option value="skip">跳过远程验证</option>
            </select>
            <p v-if="verifyMode === 'skip'" class="text-xs text-amber-600">
              跳过远程验证将无法确认 frps 端连接状态，可能导致无法自动回滚
            </p>
          </div>

          <div v-if="scanState" class="mt-4 rounded-lg border border-gray-200 p-3">
            <div class="mb-1 font-medium text-gray-900">
              状态：
              <span :class="statusClass">{{ statusLabel }}</span>
            </div>
            <div v-if="scanState.current_version" class="text-gray-600">当前版本：{{ scanState.current_version }}</div>
            <div v-if="scanState.target_version" class="text-gray-600">目标版本：{{ scanState.target_version }}</div>
            <div v-if="scanState.platform" class="text-gray-600">平台：{{ scanState.platform }}</div>
            <div v-if="scanState.frpc_bin_path" class="break-all text-gray-600">二进制：{{ scanState.frpc_bin_path }}</div>
            <div v-if="scanState.config_path" class="break-all text-gray-600">
              配置文件：
              <span class="font-mono">{{ scanState.config_path }}</span>
              <span :class="configFormatClass">({{ scanState.config_format }})</span>
            </div>
            <div v-if="scanState.has_ini || scanState.has_toml" class="text-gray-600">
              检测到配置：
              <span v-if="scanState.has_ini" class="mr-2">frpc.ini</span>
              <span v-if="scanState.has_toml">frpc.toml</span>
            </div>
            <div v-if="scanState.rollback_capable !== undefined" class="text-gray-600">
              回滚能力：
              <span :class="scanState.rollback_capable ? 'text-green-600' : 'text-amber-600'">
                {{ scanState.rollback_capable ? '支持' : '不支持' }}
              </span>
            </div>
            <div v-if="scanState.message" class="mt-1 text-gray-500">{{ scanState.message }}</div>
          </div>

          <div v-if="upgradeResult" class="mt-4 rounded-lg border p-3" :class="upgradeResult.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'">
            <div class="font-medium" :class="upgradeResult.success ? 'text-green-800' : 'text-red-800'">
              {{ upgradeResult.success ? '升级成功' : upgradeResult.rolled_back ? '已回滚' : '升级失败' }}
            </div>
            <div v-if="upgradeResult.message" class="mt-1" :class="upgradeResult.success ? 'text-green-700' : 'text-red-700'">
              {{ upgradeResult.message }}
            </div>
            <div v-if="upgradeResult.current_version" class="text-gray-600">当前版本：{{ upgradeResult.current_version }}</div>
            <div v-if="upgradeResult.backup_dir" class="break-all text-gray-600">备份目录：{{ upgradeResult.backup_dir }}</div>
          </div>
        </div>
        <div class="sticky bottom-0 z-10 flex shrink-0 flex-col gap-2 border-t border-gray-200 bg-gray-50 px-4 py-3.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:gap-2 sm:px-5">
          <button
            type="button"
            class="inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 sm:w-auto"
            :disabled="!credentialId || scanning"
            @click="runScan"
          >
            {{ scanning ? '扫描中...' : '扫描' }}
          </button>
          <button
            type="button"
            class="inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 sm:w-auto"
            aria-label="执行客户端升级"
            :disabled="!canUpgrade || upgrading"
            @click="runUpgrade"
          >
            {{ upgrading ? '升级中...' : '执行升级' }}
          </button>
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
const verifyMode = ref('agent_callback')
const scanning = ref(false)
const upgrading = ref(false)
const scanState = ref(null)
const upgradeResult = ref(null)

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
  rolled_back: '已回滚',
  upgrade_failed: '升级失败',
  unknown: '未知'
}

const statusLabel = computed(() => STATUS_LABELS[scanState.value?.status] || scanState.value?.status || '-')

const statusClass = computed(() => {
  const s = scanState.value?.status
  if (s === 'upgradeable') return 'text-green-700'
  if (s === 'latest' || s === 'upgraded') return 'text-blue-700'
  if (s === 'rolled_back') return 'text-amber-700'
  if (s === 'not_ssh') return 'text-gray-600'
  return 'text-amber-700'
})

const configFormatClass = computed(() => {
  const fmt = scanState.value?.config_format
  if (fmt === 'toml') return 'ml-1 text-blue-600'
  if (fmt === 'ini') return 'ml-1 text-purple-600'
  return 'ml-1 text-gray-500'
})

watch(visible, (v) => {
  if (v) {
    scanState.value = null
    upgradeResult.value = null
    installPath.value = '/opt/frp'
    verifyMode.value = 'agent_callback'
  }
})

function close() {
  visible.value = false
}

async function runScan() {
  if (!props.proxy?.id || !credentialId.value) return
  scanning.value = true
  upgradeResult.value = null
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
  const warnMsg = `将备份 frpc 二进制和现有配置文件。若升级后代理无法重新上线，目标主机上的升级脚本会自动回退。\n\n确认升级？`
  if (!confirm(warnMsg)) return
  upgrading.value = true
  try {
    const result = await clientUpgradeApi.upgradeProxy(props.proxy.id, {
      credential_id: credentialId.value,
      install_path: installPath.value,
      verify_mode: verifyMode.value,
      skip_remote_verify: verifyMode.value === 'skip'
    })
    upgradeResult.value = result
    if (result.success) {
      scanState.value = { ...scanState.value, status: 'upgraded', message: result.message, current_version: result.current_version }
      emit('upgraded')
    } else if (result.rolled_back) {
      scanState.value = { ...scanState.value, status: 'rolled_back', message: result.message, upgradeable: true }
    } else {
      scanState.value = { ...scanState.value, status: result.status, message: result.message, upgradeable: false }
    }
  } catch (e) {
    alert(e.message || '升级失败')
  } finally {
    upgrading.value = false
  }
}

defineExpose({ isSshCandidateProxy })
</script>
