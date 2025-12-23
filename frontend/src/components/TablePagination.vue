<template>
  <div v-if="total > 0" class="d-flex align-items-center justify-content-between flex-wrap gap-2">
    <div class="d-flex align-items-center gap-2">
      <span class="text-muted">显示</span>
      <select class="form-select form-select-sm" :value="pageSize" @change="handlePageSizeChange" style="width: auto;">
        <option :value="10">10</option>
        <option :value="20">20</option>
        <option :value="50">50</option>
        <option :value="100">100</option>
      </select>
      <span class="text-muted">条记录</span>
    </div>
    <div v-if="totalPages > 1" class="d-flex align-items-center gap-2">
      <div class="text-muted">
        显示第 {{ (page - 1) * pageSize + 1 }} - {{ Math.min(page * pageSize, total) }} 条，共 {{ total }} 条
      </div>
      <ul class="pagination mb-0">
        <li class="page-item" :class="{ disabled: page === 1 }">
          <a class="page-link" href="#" @click.prevent="goToPage(1)" :tabindex="page === 1 ? -1 : 0">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M15 6l-6 6l6 6" />
            </svg>
          </a>
        </li>
        <li class="page-item" :class="{ disabled: page === 1 }">
          <a class="page-link" href="#" @click.prevent="goToPage(page - 1)" :tabindex="page === 1 ? -1 : 0">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M15 6l-6 6l6 6" />
            </svg>
          </a>
        </li>
        
        <li v-for="pageNum in visiblePages" :key="pageNum" class="page-item" :class="{ active: pageNum === page }">
          <a class="page-link" href="#" @click.prevent="goToPage(pageNum)">
            {{ pageNum }}
          </a>
        </li>
        
        <li class="page-item" :class="{ disabled: page === totalPages }">
          <a class="page-link" href="#" @click.prevent="goToPage(page + 1)" :tabindex="page === totalPages ? -1 : 0">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M9 6l6 6l-6 6" />
            </svg>
          </a>
        </li>
        <li class="page-item" :class="{ disabled: page === totalPages }">
          <a class="page-link" href="#" @click.prevent="goToPage(totalPages)" :tabindex="page === totalPages ? -1 : 0">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M9 6l6 6l-6 6" />
            </svg>
          </a>
        </li>
      </ul>
    </div>
    <div v-else class="text-muted">
      共 {{ total }} 条记录
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  total: {
    type: Number,
    required: true,
    default: 0
  },
  page: {
    type: Number,
    required: true,
    default: 1
  },
  pageSize: {
    type: Number,
    required: true,
    default: 20
  }
})

const emit = defineEmits(['page-change', 'page-size-change'])

const totalPages = computed(() => {
  return Math.ceil(props.total / props.pageSize)
})

const handlePageSizeChange = (event) => {
  const newPageSize = parseInt(event.target.value)
  emit('page-size-change', newPageSize)
}

const visiblePages = computed(() => {
  const pages = []
  const current = props.page
  const total = totalPages.value
  const maxVisible = 7
  
  if (total <= maxVisible) {
    // 如果总页数少于等于最大显示数，显示所有页
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    // 计算显示的页码范围
    let start = Math.max(1, current - Math.floor(maxVisible / 2))
    let end = Math.min(total, start + maxVisible - 1)
    
    // 如果结束位置太靠后，调整开始位置
    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1)
    }
    
    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
  }
  
  return pages
})

const goToPage = (newPage) => {
  if (newPage >= 1 && newPage <= totalPages.value && newPage !== props.page) {
    emit('page-change', newPage)
  }
}
</script>

