<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @click.self="closeDialog"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="closeDialog"></div>
      <div
        class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-4xl flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(92vh,800px)] sm:rounded-xl"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-5 py-3.5">
          <h2 class="text-lg font-semibold text-gray-900">一键脚本生成</h2>
          <button
            type="button"
            class="btn btn-icon btn-ghost shrink-0"
            aria-label="关闭"
            @click="closeDialog"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
            <div class="grid gap-4">
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700">安装包</label>
                <select
                  v-model.number="packageId"
                  class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                >
                  <option :value="0">请选择安装包</option>
                  <option v-for="p in packages" :key="p.id" :value="p.id">
                    {{ p.version }} / {{ p.platform }} / {{ p.filename }}
                  </option>
                </select>
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700">API Key</label>
                <select
                  v-if="availableKeys.length > 0"
                  v-model.number="selectedKeyId"
                  class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                >
                  <option v-for="k in availableKeys" :key="k.id" :value="k.id">
                    #{{ k.id }} {{ k.description }}
                  </option>
                </select>
                <input
                  v-else
                  v-model="manualApiKey"
                  class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                  type="text"
                  placeholder="没有可用的 API Key，请手动输入"
                />
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700">安装路径</label>
                <input v-model="installPath" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200" type="text" />
              </div>
              <div v-if="activeTab === 'install'">
                <label class="mb-1 block text-sm font-medium text-gray-700">配置URL（可选）</label>
                <input
                  v-model="configUrl"
                  class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                  type="text"
                  placeholder="http://.../frpc.toml"
                />
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="btn btn-md"
                  :class="activeTab === 'install' ? 'btn-primary' : 'btn-outline-primary'"
                  :disabled="loading"
                  @click="activeTab = 'install'"
                >
                  安装脚本
                </button>
                <button
                  type="button"
                  class="btn btn-md"
                  :class="activeTab === 'upgrade' ? 'btn-success' : 'btn-outline-success'"
                  :disabled="loading"
                  @click="activeTab = 'upgrade'"
                >
                  升级脚本
                </button>
              </div>
              <div>
                <button
                  v-if="activeTab === 'install'"
                  type="button"
                  class="btn btn-md btn-primary"
                  :disabled="loading"
                  @click="submit"
                >
                  {{ loading ? '生成中...' : '生成安装脚本' }}
                </button>
                <button
                  v-else
                  type="button"
                  class="btn btn-md btn-success"
                  :disabled="loading"
                  @click="submitUpgrade"
                >
                  {{ loading ? '生成中...' : '生成升级脚本' }}
                </button>
              </div>
              <div v-if="activeTab === 'install' && script">
                <label class="mb-1 block text-sm font-medium text-gray-700">安装脚本预览</label>
                <CodeEditor :model-value="script" language="shell" :height="'320px'" :readonly="true" />
                <button
                  type="button"
                  class="btn btn-sm btn-outline-primary mt-2"
                  :disabled="!packageId"
                  @click="handleCopyCommand($event)"
                >
                  复制安装命令
                </button>
              </div>
              <div v-if="activeTab === 'upgrade' && upgradeScript">
                <label class="mb-1 block text-sm font-medium text-gray-700">升级脚本预览</label>
                <CodeEditor :model-value="upgradeScript" language="shell" :height="'320px'" :readonly="true" />
                <button
                  type="button"
                  class="btn btn-sm btn-outline-success mt-2"
                  :disabled="!packageId"
                  @click="handleCopyUpgradeCommand($event)"
                >
                  复制升级命令
                </button>
              </div>
            </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useModal } from '@/composables/useModal'
import { useApiKeysStore } from '@/stores/apiKeys'
import { packagesApi } from '@/api/packages'
import { copyWithTooltip } from '@/composables/useCopyTooltip'
import CodeEditor from '@/components/CodeEditor.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  packages: { type: Array, default: () => [] },
  /** 与「版本」筛选中的「最新」一致，用于默认选中对应安装包 */
  latestVersion: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  script: { type: String, default: '' },
  upgradeScript: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'submit', 'submit-upgrade'])
const apiKeysStore = useApiKeysStore()
const visible = ref(false)
const packageId = ref(0)
const installPath = ref('/opt/frp')
const configUrl = ref('')
const selectedKeyId = ref(0)
const manualApiKey = ref('')
const activeTab = ref('install')

const availableKeys = computed(() => {
  return apiKeysStore.availableKeys
})

const resolveApiKey = async () => {
  if (availableKeys.value.length === 0) {
    return manualApiKey.value.trim()
  }
  const id = selectedKeyId.value
  if (!id) return ''
  const selectedFullKey = await apiKeysStore.resolveFullKey(id)
  if (selectedFullKey) {
    return selectedFullKey
  }

  // 兜底：若当前选中的默认 Key 无法恢复完整值，则尝试其他可用默认项
  const fallbackFullKey = await apiKeysStore.resolveDefaultFullKey()
  if (fallbackFullKey) {
    selectedKeyId.value = apiKeysStore.selectedKeyId || selectedKeyId.value
    return fallbackFullKey
  }
  return ''
}

const pickDefaultPackageId = () => {
  const list = props.packages || []
  if (!list.length) return 0
  const lv = (props.latestVersion || '').trim()
  if (lv) {
    const hit = list.find((p) => p.version === lv)
    if (hit) return hit.id
  }
  return list[0].id
}

watch(() => props.modelValue, async (val) => {
  visible.value = val
  if (val) {
    activeTab.value = 'install'
    await apiKeysStore.loadKeys()
    const fallbackId = apiKeysStore.selectedKeyId || (availableKeys.value[0]?.id ?? 0)
    selectedKeyId.value = fallbackId
    if (fallbackId) {
      apiKeysStore.setDefaultKey(fallbackId)
    }
    manualApiKey.value = ''
    packageId.value = pickDefaultPackageId()
  }
})

watch(
  () => [visible.value, props.packages, props.latestVersion],
  () => {
    if (!visible.value) return
    const list = props.packages || []
    if (!list.length) {
      packageId.value = 0
      return
    }
    if (!packageId.value || !list.some((p) => p.id === packageId.value)) {
      packageId.value = pickDefaultPackageId()
    }
  },
  { deep: true }
)

watch(visible, (val) => emit('update:modelValue', val))
watch(selectedKeyId, (id) => {
  if (id) {
    apiKeysStore.setDefaultKey(id)
  }
})

const closeDialog = () => { visible.value = false }
useModal(visible, closeDialog)

const submit = async () => {
  if (!packageId.value) {
    alert('请选择安装包')
    return
  }
  if (availableKeys.value.length > 0 && !selectedKeyId.value) {
    alert('请选择 API Key')
    return
  }
  if (availableKeys.value.length === 0 && !manualApiKey.value.trim()) {
    alert('请输入 API Key（安装脚本中的下载链接需要 API Key 认证）')
    return
  }
  const apiKey = await resolveApiKey()
  if (!apiKey) {
    alert('未能获取有效的 API Key，请到"密钥管理"页重新复制/设置默认 APPKey 后重试')
    return
  }
  emit('submit', {
    package_id: packageId.value,
    api_key: apiKey || '',
    install_path: installPath.value,
    config_url: configUrl.value
  })
}

const handleCopyCommand = async (event) => {
  if (!packageId.value) return
  const apiKey = await resolveApiKey()
  if (!apiKey) {
    alert('未能获取有效的 API Key，请到"密钥管理"页重新复制/设置默认 APPKey 后重试')
    return
  }
  const url = packagesApi.getInstallScriptUrl({
    package_id: packageId.value,
    api_key: apiKey || '',
    install_path: installPath.value,
    config_url: configUrl.value || undefined
  })
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`
  await copyWithTooltip(cmd, event)
}

const submitUpgrade = async () => {
  if (!packageId.value) {
    alert('请选择安装包')
    return
  }
  if (availableKeys.value.length > 0 && !selectedKeyId.value) {
    alert('请选择 API Key')
    return
  }
  if (availableKeys.value.length === 0 && !manualApiKey.value.trim()) {
    alert('请输入 API Key（升级脚本中的下载链接需要 API Key 认证）')
    return
  }
  const apiKey = await resolveApiKey()
  if (!apiKey) {
    alert('未能获取有效的 API Key，请到"密钥管理"页重新复制/设置默认 APPKey 后重试')
    return
  }
  emit('submit-upgrade', {
    package_id: packageId.value,
    api_key: apiKey || '',
    install_path: installPath.value
  })
}

const handleCopyUpgradeCommand = async (event) => {
  if (!packageId.value) return
  const apiKey = await resolveApiKey()
  if (!apiKey) {
    alert('未能获取有效的 API Key，请到"密钥管理"页重新复制/设置默认 APPKey 后重试')
    return
  }
  const url = packagesApi.getUpgradeScriptUrl({
    package_id: packageId.value,
    api_key: apiKey || '',
    install_path: installPath.value
  })
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`
  await copyWithTooltip(cmd, event)
}
</script>
