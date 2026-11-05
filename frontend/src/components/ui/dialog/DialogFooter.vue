<script setup>
import { cn } from "cn";
import { DialogClose } from "reka-ui";
import { Button } from "@/components/ui/button";

const props = defineProps({
  class: {
    type: [Boolean, null, String, Object, Array],
    required: false,
    skipCheck: true,
  },
  showCloseButton: { type: Boolean, required: false, default: false },
});
</script>

<template>
  <div
    data-slot="dialog-footer"
    :class="
      cn(
        'shrink-0 border-t bg-muted/30 p-4 flex flex-wrap items-center justify-end gap-2',
        props.class,
      )
    "
  >
    <slot />
    <DialogClose v-if="showCloseButton" as-child>
      <Button variant="outline"> Close </Button>
    </DialogClose>
  </div>
</template>
