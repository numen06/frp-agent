<template>
  <div class="app-select" :class="[sizeClass, { 'is-disabled': disabled }]">
    <select
      class="app-select-native"
      :value="modelValue"
      :disabled="disabled"
      :required="required"
      v-bind="$attrs"
      @change="handleChange"
    >
      <slot />
    </select>
    <svg class="app-select-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.512a.75.75 0 0 1-1.08 0L5.21 8.27a.75.75 0 0 1 .02-1.06z" clip-rule="evenodd" />
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

defineOptions({
  inheritAttrs: false
})

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean, Object, null],
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  required: {
    type: Boolean,
    default: false
  },
  number: {
    type: Boolean,
    default: false
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md'].includes(value)
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const sizeClass = computed(() => (props.size === 'sm' ? 'size-sm' : 'size-md'))

const handleChange = (event) => {
  const { value } = event.target
  let nextValue = value
  if (props.number || typeof props.modelValue === 'number' || value === '') {
    nextValue = value === '' ? null : Number(value)
  }
  emit('update:modelValue', nextValue)
  emit('change', event)
}
</script>

<style scoped>
.app-select {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
}

.app-select-native {
  width: 100%;
  min-width: 0;
  appearance: none;
  border: 1px solid rgb(209 213 219);
  border-radius: 0.5rem;
  background-color: #fff;
  color: rgb(17 24 39);
  padding-right: 2rem;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.app-select-native:focus {
  border-color: rgb(59 130 246);
  box-shadow: 0 0 0 2px rgb(191 219 254);
}

.app-select-native:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  background-color: rgb(249 250 251);
}

.app-select-icon {
  position: absolute;
  right: 0.625rem;
  width: 1rem;
  height: 1rem;
  color: rgb(107 114 128);
  pointer-events: none;
}

.size-sm .app-select-native {
  font-size: 0.75rem;
  line-height: 1rem;
  padding: 0.375rem 2rem 0.375rem 0.625rem;
}

.size-md .app-select-native {
  font-size: 0.875rem;
  line-height: 1.25rem;
  padding: 0.5rem 2rem 0.5rem 0.75rem;
}

.is-disabled .app-select-icon {
  color: rgb(156 163 175);
}
</style>
