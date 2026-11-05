<script setup>
import { cn } from "cn";

const props = defineProps({
  class: {
    type: [Boolean, null, String, Object, Array],
    required: false,
    skipCheck: true,
  },
});
</script>

<template>
  <div
    data-slot="dialog-header"
    :class="
      cn(
        'flex shrink-0 flex-col gap-2 border-b p-5 pr-14 text-left',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
