<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-backdrop fade show" @click="closeDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: visible }" tabindex="-1" role="dialog" @click.self="closeDialog">
      <div class="modal-dialog modal-lg modal-dialog-centered" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">平台脚本模板编辑</h5>
            <button type="button" class="btn-close" @click="closeDialog"></button>
          </div>
          <div class="modal-body">
            <div class="grid gap-3">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <select v-model="platform" class="form-control">
                  <option value="">请选择平台</option>
                  <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
                </select>
                <button class="btn btn-outline-primary" @click="loadTemplate">加载模板</button>
                <button class="btn btn-primary" :disabled="saving" @click="saveTemplate">
                  {{ saving ? '保存中...' : '保存模板' }}
                </button>
              </div>
              <div class="code-editor-wrapper">
                <CodeEditor
                  v-model="content"
                  language="shell"
                  :height="editorHeight"
                  placeholder="可用变量：{{filename}} {{download_url}} {{install_path}} {{config_line}} {{platform}} {{version}}"
                />
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
import CodeEditor from '@/components/CodeEditor.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  platforms: { type: Array, default: () => [] },
  templates: { type: Object, default: () => ({}) },
  saving: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'save'])
const visible = ref(false)
const platform = ref('')
const content = ref('')
const editorHeight = ref('420px')

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => emit('update:modelValue', val))

const closeDialog = () => { visible.value = false }
useModal(visible, closeDialog)

const loadTemplate = () => {
  if (!platform.value) {
    alert('请先选择平台')
    return
  }
  content.value = props.templates[platform.value] || ''
}

const saveTemplate = () => {
  if (!platform.value || !content.value.trim()) {
    alert('请选择平台并填写脚本内容')
    return
  }
  emit('save', { platform: platform.value, content: content.value })
}
</script>

<style scoped>
.code-editor-wrapper {
  border-radius: 8px;
  overflow: hidden;
}
</style>
