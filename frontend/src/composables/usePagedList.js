import { reactive, ref } from 'vue'

export function usePagedList(fetchPage) {
  const items = ref([])
  const pagination = reactive({ page: 1, page_size: 20, total: 0 })
  const search = ref('')
  const loading = ref(false)
  const error = ref('')
  let requestId = 0

  async function load(page = pagination.page) {
    const id = ++requestId
    loading.value = true
    error.value = ''
    try {
      const data = await fetchPage({ page, page_size: pagination.page_size, search: search.value || undefined })
      if (id !== requestId) return
      const lastPage = Math.max(1, Math.ceil(data.total / pagination.page_size))
      if (page > lastPage) return await load(lastPage)
      items.value = data.items
      Object.assign(pagination, { page: data.page, page_size: data.page_size, total: data.total })
    } catch (e) {
      if (id === requestId) error.value = e.message || '加载失败，请重试'
    } finally {
      if (id === requestId) loading.value = false
    }
  }
  function resize(size) {
    pagination.page_size = size
    return load(1)
  }
  return { items, pagination, search, loading, error, load, resize }
}
