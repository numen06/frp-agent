import { computed, reactive, watch } from 'vue'

// For finite results already held by an upload/import operation, never database lists.
export function useLocalPagination(source) {
  const pagination = reactive({ page: 1, page_size: 20, total: 0 })
  watch(() => source.value.length, total => {
    pagination.total = total
    pagination.page = Math.min(pagination.page, Math.max(1, Math.ceil(total / pagination.page_size)))
  }, { immediate: true })
  const items = computed(() => source.value.slice((pagination.page - 1) * pagination.page_size, pagination.page * pagination.page_size))
  const load = page => { pagination.page = page }
  const resize = size => { pagination.page_size = size; pagination.page = 1 }
  return { items, pagination, load, resize }
}
