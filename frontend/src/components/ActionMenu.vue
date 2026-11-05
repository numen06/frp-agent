<script setup>
import { ChevronDown, MoreHorizontal } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
defineProps({
  items: { type: Array, default: () => [] },
  label: { type: String, default: "更多操作" },
  text: String,
  variant: { type: String, default: "ghost" },
  disabled: Boolean,
  align: { type: String, default: "end" },
});
const emit = defineEmits(["select"]);
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <slot name="trigger"
        ><Button
          type="button"
          :variant="variant"
          :size="text ? 'default' : 'icon-sm'"
          :aria-label="label"
          :disabled="disabled"
          ><template v-if="text"
            >{{ text }}<ChevronDown class="size-4" /></template
          ><MoreHorizontal v-else class="size-4" /></Button
      ></slot> </DropdownMenuTrigger
    ><DropdownMenuContent
      :align="align"
      :collision-padding="12"
      class="min-w-44 max-w-[calc(100vw-2rem)]"
    >
      <slot name="content">
        <template v-for="item in items" :key="item.action || item.label">
          <DropdownMenuSeparator v-if="item.separator" /><DropdownMenuItem
            v-else
            :disabled="item.disabled"
            :variant="item.danger ? 'destructive' : undefined"
            @select="(event) => emit('select', item.action, event)"
            >{{ item.label }}</DropdownMenuItem
          >
        </template>
      </slot>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
