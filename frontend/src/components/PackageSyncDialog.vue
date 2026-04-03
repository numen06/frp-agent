<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-backdrop fade show" @click="closeDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: visible }" tabindex="-1" role="dialog" @click.self="closeDialog">
      <div class="modal-dialog modal-dialog-centered" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">从 GitHub 同步安装包</h5>
            <button type="button" class="btn-close" @click="closeDialog"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">版本</label>
              <select v-model="form.version" class="form-control">
                <option value="">请选择版本</option>
                <option v-for="item in releases" :key="item.version" :value="item.version">
                  {{ item.version }}
                </option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">平台（可多选）</label>
              <div v-if="platformsForVersion.length" class="flex gap-2 mb-2">
                <button type="button" class="btn btn-sm btn-outline-primary" @click="selectAll">全选</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" @click="deselectAll">取消全选</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" @click="invertSelection">反选</button>
                <span class="form-label mb-0 ms-auto">已选 {{ form.platforms.length }} / {{ platformsForVersion.length }}</span>
              </div>
              <div class="grid gap-2" style="max-height: 260px; overflow-y: auto;">
                <label v-for="p in platformsForVersion" :key="p" class="form-check">
                  <input v-model="form.platforms" class="form-check-input" type="checkbox" :value="p" />
                  <span class="form-check-label">{{ p }}</span>
                </label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn" @click="closeDialog">取消</button>
            <button type="button" class="btn btn-primary" :disabled="loading" @click="submit">
              {{ loading ? '同步中...' : '开始同步' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  releases: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'submit'])
const visible = ref(false)
const form = reactive({
  version: '',
  platforms: []
})

const platformsForVersion = computed(() => {
  const rel = props.releases.find((r) => r.version === form.version)
  return rel?.platforms?.length ? rel.platforms : []
})

watch(() => props.modelValue, (val) => {
  visible.value = val
})
watch(visible, (val) => emit('update:modelValue', val))

watch(
  () => [form.version, props.releases],
  () => {
    const list = platformsForVersion.value
    form.platforms = list.length ? [...list] : []
  },
  { deep: true }
)

const closeDialog = () => {
  visible.value = false
}

useModal(visible, closeDialog)

const selectAll = () => {
  form.platforms = [...platformsForVersion.value]
}
const deselectAll = () => {
  form.platforms = []
}
const invertSelection = () => {
  const all = platformsForVersion.value
  form.platforms = all.filter((p) => !form.platforms.includes(p))
}

const submit = () => {
  if (!form.version) {
    alert('请选择版本')
    return
  }
  emit('submit', { version: form.version, platforms: form.platforms })
}
</script>
