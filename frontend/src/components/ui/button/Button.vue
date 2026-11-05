<script setup>
import { cn } from "cn";
import { Primitive } from "reka-ui";
import { buttonVariants } from ".";
import { useAttrs } from "vue";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

defineOptions({ inheritAttrs: false });
const attrs = useAttrs();

const props = defineProps({
  variant: { type: null, required: false },
  size: { type: null, required: false },
  class: {
    type: [Boolean, null, String, Object, Array],
    required: false,
    skipCheck: true,
  },
  asChild: { type: Boolean, required: false },
  as: { type: null, required: false, default: "button" },
  tooltip: { type: String, required: false },
});
function tooltipText() {
  return (
    props.tooltip ||
    (String(props.size || "").startsWith("icon")
      ? attrs["aria-label"] || attrs.title
      : "")
  );
}
</script>

<template>
  <Tooltip v-if="tooltipText()" :delay-duration="200">
    <TooltipTrigger as-child>
      <Primitive
        v-bind="attrs"
        :title="undefined"
        data-slot="button"
        :aria-label="attrs['aria-label'] || tooltipText()"
        :data-variant="variant"
        :data-size="size"
        :as="as"
        :as-child="asChild"
        :class="cn(buttonVariants({ variant, size }), props.class)"
        ><slot
      /></Primitive>
    </TooltipTrigger>
    <TooltipContent>{{ tooltipText() }}</TooltipContent>
  </Tooltip>
  <Primitive
    v-else
    v-bind="attrs"
    data-slot="button"
    :data-variant="variant"
    :data-size="size"
    :as="as"
    :as-child="asChild"
    :class="cn(buttonVariants({ variant, size }), props.class)"
  >
    <slot />
  </Primitive>
</template>
