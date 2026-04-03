<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-backdrop fade show" @click="closeDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: visible }" tabindex="-1" role="dialog" @click.self="closeDialog">
      <div class="modal-dialog modal-lg modal-dialog-centered" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">生成一键安装脚本</h5>
            <button type="button" class="btn-close" @click="closeDialog"></button>
          </div>
          <div class="modal-body">
            <div class="grid gap-3">
              <div>
                <label class="form-label">安装包</label>
                <select v-model.number="packageId" class="form-control">
                  <option :value="0">请选择安装包</option>
                  <option v-for="p in packages" :key="p.id" :value="p.id">
                    {{ p.version }} / {{ p.platform }} / {{ p.filename }}
                  </option>
                </select>
              </div>
              <div>
                <label class="form-label">API Key</label>
                <select v-if="availableKeys.length > 0" v-model.number="selectedKeyId" class="form-control">
                  <option v-for="k in availableKeys" :key="k.id" :value="k.id">
                    #{{ k.id }} {{ k.description }}
                  </option>
                </select>
                <input v-else v-model="manualApiKey" class="form-control" type="text" placeholder="没有可用的 API Key，请手动输入" />
              </div>
              <div>
                <label class="form-label">安装路径</label>
                <input v-model="installPath" class="form-control" type="text" />
              </div>
              <div>
                <label class="form-label">配置URL（可选）</label>
                <input v-model="configUrl" class="form-control" type="text" placeholder="http://.../frpc.toml" />
              </div>
              <div>
                <button class="btn btn-primary" :disabled="loading" @click="submit">{{ loading ? '生成中...' : '生成脚本' }}</button>
              </div>
              <div v-if="script">
                <label class="form-label">安装脚本预览</label>
                <CodeEditor
                  :model-value="script"
                  language="shell"
                  :height="'320px'"
                  :readonly="true"
                />
                <button class="btn btn-outline-primary mt-2" :disabled="!packageId" @click="handleCopyCommand($event)">复制安装命令</button>
              </div>
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
  script: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'submit'])
const apiKeysStore = useApiKeysStore()
const visible = ref(false)
const packageId = ref(0)
const installPath = ref('/opt/frp')
const configUrl = ref('')
const selectedKeyId = ref(0)
const manualApiKey = ref('')

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
</script>
