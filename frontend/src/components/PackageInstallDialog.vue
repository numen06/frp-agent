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
                <input v-model="apiKey" class="form-control" type="text" placeholder="请输入 API Key" />
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
                <label class="form-label">安装脚本</label>
                <textarea class="form-control font-monospace" rows="10" :value="script" readonly></textarea>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  packages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  script: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'submit'])
const visible = ref(false)
const packageId = ref(0)
const apiKey = ref('')
const installPath = ref('/usr/local/bin')
const configUrl = ref('')

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => emit('update:modelValue', val))

const closeDialog = () => { visible.value = false }
useModal(visible, closeDialog)

const submit = () => {
  if (!packageId.value || !apiKey.value) {
    alert('请选择安装包并输入 API Key')
    return
  }
  emit('submit', {
    package_id: packageId.value,
    api_key: apiKey.value,
    install_path: installPath.value,
    config_url: configUrl.value
  })
}
</script>
