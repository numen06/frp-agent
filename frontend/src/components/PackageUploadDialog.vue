<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-backdrop fade show" @click="closeDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: visible }" tabindex="-1" role="dialog" @click.self="closeDialog">
      <div class="modal-dialog modal-dialog-centered" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">手动上传安装包</h5>
            <button type="button" class="btn-close" @click="closeDialog"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">版本</label>
              <input v-model="version" class="form-control" type="text" placeholder="例如 v0.61.1" />
            </div>
            <div class="mb-3">
              <label class="form-label">平台</label>
              <select v-model="platform" class="form-control">
                <option value="">请选择平台</option>
                <option v-for="p in props.platforms" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">文件</label>
              <input class="form-control" type="file" @change="onFileChange" />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn" @click="closeDialog">取消</button>
            <button type="button" class="btn btn-primary" :disabled="loading" @click="submit">
              {{ loading ? '上传中...' : '上传' }}
            </button>
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
  platforms: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'submit'])

const visible = ref(false)
const version = ref('')
const platform = ref('')
const file = ref(null)

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => emit('update:modelValue', val))

const closeDialog = () => { visible.value = false }
useModal(visible, closeDialog)

const onFileChange = (e) => {
  file.value = e.target.files?.[0] || null
}

const submit = () => {
  if (!version.value || !platform.value || !file.value) {
    alert('请填写完整信息并选择文件')
    return
  }
  emit('submit', { version: version.value, platform: platform.value, file: file.value })
}
</script>
