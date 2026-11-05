<script setup>
import { computed } from "vue";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
const props = defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
});
const emit = defineEmits(["page-change", "page-size-change"]);
const pages = computed(() =>
  Math.max(1, Math.ceil(props.total / props.pageSize)),
);
</script>

<template>
  <div
    v-if="total > 0"
    class="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground"
  >
    <div class="flex items-center gap-2">
      <span>每页</span
      ><Select
        :model-value="pageSize"
        @update:model-value="(value) => emit('page-size-change', Number(value))"
        ><SelectTrigger class="w-20" aria-label="每页条数"
          ><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectItem
            v-for="size in [10, 20, 50, 100]"
            :key="size"
            :value="size"
            >{{ size }}</SelectItem
          ></SelectContent
        ></Select
      ><span>条 · 共 {{ total }} 条</span>
    </div>
    <Pagination
      v-if="pages > 1"
      :page="page"
      :items-per-page="pageSize"
      :total="total"
      :sibling-count="1"
      show-edges
      class="mx-0 w-auto"
      @update:page="(value) => emit('page-change', value)"
    >
      <PaginationContent v-slot="{ items }"
        ><PaginationPrevious aria-label="上一页" /><span
          class="px-2 text-xs sm:hidden"
          >{{ page }} / {{ pages }}</span
        ><template v-for="(item, index) in items" :key="index"
          ><PaginationItem
            v-if="item.type === 'page'"
            :value="item.value"
            :is-active="item.value === page"
            class="hidden sm:inline-flex"
            >{{ item.value }}</PaginationItem
          ><PaginationEllipsis v-else class="hidden sm:inline-flex" /></template
        ><PaginationNext aria-label="下一页"
      /></PaginationContent>
    </Pagination>
    <span v-else class="text-xs"
      >第 {{ (page - 1) * pageSize + 1 }}–{{
        Math.min(page * pageSize, total)
      }}
      条</span
    >
  </div>
</template>
