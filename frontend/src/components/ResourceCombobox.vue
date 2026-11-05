<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import { Check, ChevronsUpDown, LoaderCircle } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  Combobox,
  ComboboxAnchor,
  ComboboxInput,
  ComboboxItem,
  ComboboxItemIndicator,
  ComboboxList,
  ComboboxTrigger,
  ComboboxViewport,
} from "@/components/ui/combobox";

defineOptions({ inheritAttrs: false });
const props = defineProps({
  modelValue: [String, Number],
  label: { type: String, default: "选择记录" },
  disabled: Boolean,
  fetchOptions: { type: Function, required: true },
  resolveOption: Function,
  getLabel: {
    type: Function,
    default: (row) => row.name || row.description || String(row),
  },
  getValue: { type: Function, default: (row) => row.id ?? row },
  allowClear: Boolean,
  clearLabel: { type: String, default: "清除选择" },
  scopeKey: [String, Number],
});
const emit = defineEmits(["update:modelValue", "select"]);
const open = ref(false),
  selected = ref(null),
  items = ref([]),
  search = ref("");
const loading = ref(false),
  resolving = ref(false),
  error = ref(""),
  selectionError = ref("");
const page = ref(1),
  total = ref(0),
  pageSize = 20;
const clearOption = { __clear: true };
const pages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const empty = (value) => value == null || value === "" || value === 0;
const key = (row) => (row?.__clear ? "__clear__" : props.getValue(row));
const same = (a, b) => String(a) === String(b);
let request = 0,
  selectionRequest = 0,
  timer,
  disposed = false;

async function resolveSelection() {
  const id = ++selectionRequest,
    value = props.modelValue;
  selectionError.value = "";
  if (empty(value)) {
    selected.value = null;
    resolving.value = false;
    return;
  }
  if (selected.value && same(key(selected.value), value)) return;
  selected.value = null;
  resolving.value = true;
  try {
    const row = props.resolveOption
      ? await props.resolveOption(value)
      : items.value.find((row) => same(key(row), value));
    if (id !== selectionRequest || disposed) return;
    if (row == null) throw new Error("所选记录不存在或不可访问");
    selected.value = row;
  } catch (e) {
    if (id === selectionRequest && !disposed)
      selectionError.value = e.message || "选项回显失败";
  } finally {
    if (id === selectionRequest) resolving.value = false;
  }
}
async function load(nextPage = 1) {
  if (props.disabled || disposed) return;
  const id = ++request;
  loading.value = true;
  error.value = "";
  items.value = [];
  try {
    const data = await props.fetchOptions({
      page: nextPage,
      page_size: pageSize,
      search: search.value.trim() || undefined,
    });
    if (id !== request || disposed) return;
    items.value = data.items;
    total.value = data.total;
    page.value = data.page;
    if (!props.resolveOption && !selected.value && !empty(props.modelValue)) {
      const row = items.value.find((row) => same(key(row), props.modelValue));
      if (row) {
        selected.value = row;
        selectionError.value = "";
      }
    }
  } catch (e) {
    if (id === request && !disposed) error.value = e.message || "选项加载失败";
  } finally {
    if (id === request) loading.value = false;
  }
}
function choose(row) {
  if (!row || loading.value) return;
  selectionRequest++;
  const value = row.__clear ? null : row;
  selected.value = value;
  selectionError.value = "";
  resolving.value = false;
  emit("update:modelValue", value == null ? "" : props.getValue(value));
  emit("select", value);
  open.value = false;
}
watch(() => props.modelValue, resolveSelection, { immediate: true });
watch(
  () => props.scopeKey,
  (_, previous) => {
    request++;
    selectionRequest++;
    clearTimeout(timer);
    items.value = [];
    search.value = "";
    error.value = "";
    loading.value = false;
    if (previous != null && previous !== "") {
      selected.value = null;
      selectionError.value = "";
      emit("update:modelValue", "");
      emit("select", null);
    }
    if (open.value) load();
  },
);
watch(open, async (value) => {
  clearTimeout(timer);
  if (value) {
    search.value = "";
    await nextTick();
    clearTimeout(timer);
    if (open.value) load();
  } else {
    request++;
    loading.value = false;
  }
});
watch(search, () => {
  clearTimeout(timer);
  if (open.value) timer = setTimeout(() => load(1), 250);
});
watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) open.value = false;
  },
);
onUnmounted(() => {
  disposed = true;
  request++;
  selectionRequest++;
  clearTimeout(timer);
});
</script>

<template>
  <div v-bind="$attrs" class="min-w-0">
    <Combobox
      :model-value="selected"
      v-model:open="open"
      :by="(a, b) => a != null && b != null && same(key(a), key(b))"
      ignore-filter
      :reset-model-value-on-clear="false"
      :disabled="disabled"
      @update:model-value="choose"
    >
      <ComboboxAnchor as-child>
        <ComboboxTrigger as-child>
          <Button
            type="button"
            variant="outline"
            class="w-full min-w-0 justify-between text-base font-normal md:text-sm"
            :aria-label="label"
            :aria-busy="resolving"
            :disabled="disabled"
          >
            <span
              class="truncate"
              :class="!selected ? 'text-muted-foreground' : ''"
              >{{
                selected
                  ? getLabel(selected)
                  : resolving
                    ? "读取中…"
                    : selectionError
                      ? "选项读取失败"
                      : label
              }}</span
            ><LoaderCircle
              v-if="resolving"
              class="size-4 shrink-0 animate-spin"
            /><ChevronsUpDown
              v-else
              class="size-4 shrink-0 text-muted-foreground"
            />
          </Button>
        </ComboboxTrigger> </ComboboxAnchor
      ><ComboboxList
        class="flex flex-col max-h-[min(24rem,var(--reka-combobox-content-available-height))] min-w-[min(20rem,calc(100vw-2rem))] max-w-[calc(100vw-2rem)]"
        align="start"
        :collision-padding="12"
      >
        <ComboboxInput
          v-model="search"
          :aria-label="`搜索${label}`"
          placeholder="输入关键词搜索…"
        />
        <div v-if="error" class="space-y-2 p-3">
          <p role="alert" class="text-sm text-destructive">{{ error }}</p>
          <Button type="button" variant="outline" size="sm" @click="load(page)"
            >重试</Button
          >
        </div>
        <p
          v-if="loading"
          role="status"
          class="px-3 py-2 text-sm text-muted-foreground"
        >
          正在加载选项…
        </p>
        <ComboboxViewport
          class="min-h-0 min-w-0 flex-1 max-h-none overflow-x-hidden"
        >
          <ComboboxItem
            v-if="allowClear"
            :value="clearOption"
            :disabled="loading"
            >{{ clearLabel }}</ComboboxItem
          ><ComboboxItem
            v-for="row in items"
            :key="key(row)"
            :value="row"
            :disabled="loading"
            class="min-w-0"
          >
            <span
              class="line-clamp-2 min-w-0 flex-1 break-all"
              :title="getLabel(row)"
              >{{ getLabel(row) }}</span
            ><ComboboxItemIndicator
              ><Check class="size-4"
            /></ComboboxItemIndicator>
          </ComboboxItem>
          <p
            v-if="!loading && !error && !items.length"
            role="status"
            class="p-4 text-center text-sm text-muted-foreground"
          >
            没有匹配的记录
          </p>
        </ComboboxViewport>
        <div
          class="flex shrink-0 items-center justify-between gap-2 border-t p-2 text-xs text-muted-foreground"
        >
          <span>{{ page }} / {{ pages }} 页 · 共 {{ total }} 条</span>
          <div class="flex gap-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label="上一页选项"
              :disabled="loading || page <= 1"
              @pointerdown.prevent
              @click.stop="load(page - 1)"
              >上一页</Button
            ><Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label="下一页选项"
              :disabled="loading || page >= pages"
              @pointerdown.prevent
              @click.stop="load(page + 1)"
              >下一页</Button
            >
          </div>
        </div>
      </ComboboxList>
    </Combobox>
    <div v-if="selectionError" class="mt-1 flex flex-wrap items-center gap-1">
      <p role="alert" class="text-xs text-destructive">{{ selectionError }}</p>
      <Button type="button" variant="link" size="xs" @click="resolveSelection"
        >重试回显</Button
      >
    </div>
  </div>
</template>
