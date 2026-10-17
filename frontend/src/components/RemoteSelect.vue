<template>
  <button v-bind="$attrs" type="button" class="btn btn-md btn-outline w-full justify-between text-left" :disabled="disabled" :aria-label="label" :aria-expanded="open" @click="openPicker">
    <span class="min-w-0 truncate">{{ selected ? getLabel(selected) : modelValue ? `已选：${modelValue}` : label }}</span><span aria-hidden="true">⌄</span>
  </button>
  <AppDialog v-model="open" :title="label" panel-class="max-w-xl">
    <form class="mb-3 flex gap-2" @submit.prevent="list.load(1)">
      <input v-model="list.search.value" :aria-label="`搜索${label}`" placeholder="输入关键词搜索" class="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2">
      <button type="submit" class="btn btn-md btn-outline">搜索</button>
    </form>
    <p v-if="list.error.value" role="alert" class="mb-2 text-sm text-red-600">{{ list.error.value }}</p>
    <p v-if="list.loading.value" role="status" class="py-4 text-center text-sm text-gray-500">加载中…</p>
    <div v-else class="divide-y divide-gray-100">
      <button v-if="allowClear" type="button" class="btn btn-md btn-ghost w-full justify-start" @click="choose(null)">{{ clearLabel }}</button>
      <button v-for="item in list.items.value" :key="getValue(item)" type="button" class="btn btn-md btn-ghost w-full justify-start text-left" :class="getValue(item) === modelValue ? 'bg-blue-50 text-blue-700' : ''" @click="choose(item)"><span class="break-all">{{ getLabel(item) }}</span></button>
      <p v-if="!list.items.value.length" class="py-6 text-center text-sm text-gray-500">没有匹配的记录</p>
    </div>
    <template #footer><div class="w-full"><TablePagination :total="list.pagination.total" :page="list.pagination.page" :page-size="list.pagination.page_size" @page-change="list.load" @page-size-change="list.resize" /></div></template>
  </AppDialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import AppDialog from './AppDialog.vue'
import TablePagination from './TablePagination.vue'
import { usePagedList } from '@/composables/usePagedList'
defineOptions({ inheritAttrs: false })
const props = defineProps({
  modelValue: [String, Number], label: { type: String, default: '选择记录' }, disabled: Boolean,
  fetchOptions: { type: Function, required: true }, resolveOption: Function,
  getLabel: { type: Function, default: item => item.name || item.description || String(item) },
  getValue: { type: Function, default: item => item.id ?? item },
  allowClear: Boolean, clearLabel: { type: String, default: '清除选择' },
})
const emit = defineEmits(['update:modelValue', 'select'])
const selected = ref(null)
const open = ref(false)
const list = usePagedList(params => props.fetchOptions(params))
let selectionRequest = 0
watch(() => props.modelValue, async value => {
  const request = ++selectionRequest
  if (!value) { selected.value = null; return }
  if (selected.value && props.getValue(selected.value) === value) return
  if (props.resolveOption) {
    try {
      const item = await props.resolveOption(value)
      if (request === selectionRequest) selected.value = item
    } catch { if (request === selectionRequest) selected.value = null }
  }
}, { immediate: true })
function openPicker() { open.value = true; list.load(1) }
function choose(item) {
  selected.value = item
  emit('update:modelValue', item ? props.getValue(item) : '')
  emit('select', item)
  open.value = false
}
</script>
