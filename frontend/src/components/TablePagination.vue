<template>
  <div v-if="total > 0" class="flex flex-col gap-3">
    <!-- 手机端：精简分页 -->
    <div class="flex flex-col gap-2 md:hidden">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-500">每页</span>
          <AppSelect class="w-auto" size="sm" :number="true" :model-value="pageSize" @change="handlePageSizeChange">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </AppSelect>
          <span class="text-sm text-gray-500">条</span>
        </div>
        <span class="text-sm text-gray-500">共 {{ total }} 条</span>
      </div>
      <div v-if="totalPages > 1" class="flex items-center justify-between gap-2">
        <button
          type="button"
          class="btn btn-sm btn-outline min-w-[4.5rem]"
          :disabled="page === 1"
          aria-label="上一页"
          @click="goToPage(page - 1)"
        >
          上一页
        </button>
        <span class="text-sm font-medium text-gray-700">{{ page }} / {{ totalPages }}</span>
        <button
          type="button"
          class="btn btn-sm btn-outline min-w-[4.5rem]"
          :disabled="page === totalPages"
          aria-label="下一页"
          @click="goToPage(page + 1)"
        >
          下一页
        </button>
      </div>
      <div v-else class="text-center text-sm text-gray-500">
        第 {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} 条
      </div>
    </div>

    <!-- 桌面端：完整分页 -->
    <div class="hidden flex-wrap items-center justify-between gap-2 md:flex">
      <div class="flex items-center gap-2">
        <span class="text-sm text-gray-500">显示</span>
        <AppSelect class="w-auto" size="sm" :number="true" :model-value="pageSize" @change="handlePageSizeChange">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </AppSelect>
        <span class="text-sm text-gray-500">条记录</span>
      </div>
      <div v-if="totalPages > 1" class="flex items-center gap-2">
        <div class="text-sm text-gray-500">
          显示第 {{ (page - 1) * pageSize + 1 }} - {{ Math.min(page * pageSize, total) }} 条，共 {{ total }} 条
        </div>
        <ul class="inline-flex items-center gap-1">
          <li>
            <a
              class="btn-page"
              :class="{ 'pointer-events-none opacity-50': page === 1 }"
              href="#"
              @click.prevent="goToPage(1)"
              :tabindex="page === 1 ? -1 : 0"
              aria-label="第一页"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M15 6l-6 6l6 6" />
              </svg>
            </a>
          </li>
          <li>
            <a
              class="btn-page"
              :class="{ 'pointer-events-none opacity-50': page === 1 }"
              href="#"
              @click.prevent="goToPage(page - 1)"
              :tabindex="page === 1 ? -1 : 0"
              aria-label="上一页"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M15 6l-6 6l6 6" />
              </svg>
            </a>
          </li>
          <li v-for="pageNum in visiblePages" :key="pageNum">
            <a
              class="btn-page"
              :class="pageNum === page ? 'btn-page-active' : ''"
              href="#"
              @click.prevent="goToPage(pageNum)"
            >
              {{ pageNum }}
            </a>
          </li>
          <li>
            <a
              class="btn-page"
              :class="{ 'pointer-events-none opacity-50': page === totalPages }"
              href="#"
              @click.prevent="goToPage(page + 1)"
              :tabindex="page === totalPages ? -1 : 0"
              aria-label="下一页"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M9 6l6 6l-6 6" />
              </svg>
            </a>
          </li>
          <li>
            <a
              class="btn-page"
              :class="{ 'pointer-events-none opacity-50': page === totalPages }"
              href="#"
              @click.prevent="goToPage(totalPages)"
              :tabindex="page === totalPages ? -1 : 0"
              aria-label="最后一页"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M9 6l6 6l-6 6" />
              </svg>
            </a>
          </li>
        </ul>
      </div>
      <div v-else class="text-sm text-gray-500">
        共 {{ total }} 条记录
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppSelect from '@/components/AppSelect.vue'

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
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    let start = Math.max(1, current - Math.floor(maxVisible / 2))
    let end = Math.min(total, start + maxVisible - 1)
    
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
