<template>
  <Teleport to="body">
    <div v-if="modelValue" ref="root" class="app-dialog fixed inset-0 z-[70] flex items-center justify-center p-4" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1" @keydown.tab="trapFocus">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="close"></div>
      <div class="app-dialog-panel relative z-10 flex max-h-[90dvh] w-full flex-col overflow-hidden rounded-xl bg-white shadow-xl" :class="panelClass">
        <div class="app-dialog-header flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-5 py-3">
          <h2 class="font-semibold">{{ title }}</h2>
          <button type="button" class="btn btn-icon btn-ghost" aria-label="关闭" :disabled="busy" @click="close">×</button>
        </div>
        <div class="app-dialog-body min-h-0 overflow-auto p-4"><slot /></div>
        <div v-if="$slots.footer" class="app-dialog-footer flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 p-4"><slot name="footer" /></div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useModal } from '@/composables/useModal'
const props = defineProps({ modelValue: Boolean, title: { type: String, required: true }, busy: Boolean, panelClass: { type: String, default: 'max-w-3xl' } })
const emit = defineEmits(['update:modelValue'])
const root = ref(null)
let previousFocus
function close() { if (!props.busy) emit('update:modelValue', false) }
useModal(computed(() => props.modelValue), close, { disabled: () => props.busy })
watch(() => props.modelValue, async visible => {
  if (visible) {
    previousFocus = document.activeElement
    await nextTick()
    root.value?.focus()
  } else previousFocus?.focus?.()
})
function trapFocus(event) {
  const controls = [...root.value.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]')].filter(el => el.getClientRects().length)
  const first = controls[0], last = controls.at(-1)
  if (!first) { event.preventDefault(); return }
  if (event.shiftKey && (document.activeElement === first || document.activeElement === root.value)) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && (document.activeElement === last || document.activeElement === root.value)) { event.preventDefault(); first.focus() }
}
</script>
