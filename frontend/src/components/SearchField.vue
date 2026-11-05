<script setup>
import { onUnmounted } from "vue";
import { Search, X } from "@lucide/vue";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
const props = defineProps({
  modelValue: { type: String, default: "" },
  placeholder: { type: String, default: "输入关键词搜索" },
  label: { type: String, default: "搜索" },
  debounce: { type: Number, default: 0 },
});
const emit = defineEmits(["update:modelValue", "search"]);
let timer;
function update(value) {
  clearTimeout(timer);
  emit("update:modelValue", value);
  if (props.debounce > 0)
    timer = setTimeout(() => emit("search", value), props.debounce);
}
function search() {
  clearTimeout(timer);
  emit("search", props.modelValue);
}
function onEnter(event) {
  if (!event.isComposing) {
    event.preventDefault();
    search();
  }
}
function clear() {
  clearTimeout(timer);
  emit("update:modelValue", "");
  emit("search", "");
}
onUnmounted(() => clearTimeout(timer));
</script>

<template>
  <InputGroup class="min-w-0">
    <InputGroupAddon><Search class="size-4" /></InputGroupAddon
    ><InputGroupInput
      :model-value="modelValue"
      :placeholder="placeholder"
      :aria-label="label"
      @update:model-value="update"
      @keydown.enter="onEnter"
    /><InputGroupAddon v-if="modelValue" align="inline-end"
      ><InputGroupButton
        type="button"
        variant="ghost"
        size="icon-xs"
        aria-label="清除搜索"
        @click="clear"
        ><X class="size-4" /></InputGroupButton
    ></InputGroupAddon>
  </InputGroup>
</template>
