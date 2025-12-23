<template>
  <div class="dropdown" :class="dropdownClass">
    <button 
      ref="triggerRef"
      class="btn dropdown-toggle"
      :class="buttonClass"
      @click.prevent="toggle"
      :aria-expanded="isOpen"
      type="button"
    >
      <slot name="trigger">{{ label }}</slot>
    </button>
    <div 
      ref="dropdownRef"
      class="dropdown-menu"
      :class="menuClass"
      :class="{ show: isOpen }"
      @click.stop
    >
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { useDropdown } from '@/composables/useDropdown'

const props = defineProps({
  label: {
    type: String,
    default: '操作'
  },
  buttonClass: {
    type: String,
    default: ''
  },
  menuClass: {
    type: String,
    default: ''
  },
  dropdownClass: {
    type: String,
    default: ''
  }
})

const { isOpen, dropdownRef, triggerRef, toggle, close } = useDropdown()

// 暴露 close 方法供父组件调用
defineExpose({
  close
})
</script>

