<script setup>
import { reactiveOmit } from "@vueuse/core";
import { cn } from "cn";
import { ComboboxItemIndicator, useForwardProps } from "reka-ui";

const props = defineProps({
  forceMount: { type: Boolean, required: false },
  asChild: { type: Boolean, required: false },
  as: { type: null, required: false },
  class: {
    type: [Boolean, null, String, Object, Array],
    required: false,
    skipCheck: true,
  },
});

const delegatedProps = reactiveOmit(props, "class");

const forwarded = useForwardProps(delegatedProps);
</script>

<template>
  <ComboboxItemIndicator
    data-slot="combobox-item-indicator"
    v-bind="forwarded"
    :class="
      cn(
        'pointer-events-none absolute right-2 flex size-4 items-center justify-center',
        props.class,
      )
    "
  >
    <slot />
  </ComboboxItemIndicator>
</template>
