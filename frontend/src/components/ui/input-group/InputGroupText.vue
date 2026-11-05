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
  <span
    :class="
      cn(
        'text-muted-foreground gap-2 text-sm [&_svg:not([class*=size-])]:size-4 flex items-center [&_svg]:pointer-events-none',
        props.class,
      )
    "
  >
    <slot />
  </span>
</template>
