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
    data-slot="card-header"
    :class="
      cn(
        'flex flex-wrap items-center justify-between gap-3 border-b p-5',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
