<template>
  <div class="flex w-full items-stretch">
    <span class="inline-flex items-center rounded-l-lg border border-r-0 border-gray-300 bg-gray-50 px-3 text-gray-500">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
        <path d="M21 21l-6 -6" />
      </svg>
    </span>
    <input
      type="text"
      class="block w-full border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
      :placeholder="placeholder"
      :value="modelValue"
      @input="onInput"
      @keyup.enter="triggerSearch"
    />
    <button
      v-if="modelValue"
      class="inline-flex items-center justify-center rounded-r-lg border border-l-0 border-gray-300 px-3 text-gray-600 hover:bg-gray-100"
      type="button"
      @click="clear"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M18 6l-12 12" />
        <path d="M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '搜索...'
  },
  debounce: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:modelValue', 'search'])

let debounceTimer = null

const triggerSearch = () => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  emit('search', props.modelValue)
}

const onInput = (event) => {
  const value = event.target.value
  emit('update:modelValue', value)
  if (props.debounce > 0) {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      emit('search', value)
    }, props.debounce)
  }
}

const clear = () => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  emit('update:modelValue', '')
  emit('search', '')
}

onUnmounted(() => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
})
</script>
