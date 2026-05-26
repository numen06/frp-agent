<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
    aria-hidden="true"
  >
    <template v-if="name === 'dashboard'">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </template>
    <template v-else-if="name === 'proxies'">
      <path d="M4 6h16" />
      <path d="M4 12h16" />
      <path d="M4 18h10" />
      <circle cx="19" cy="18" r="2" />
    </template>
    <template v-else-if="name === 'groups'">
      <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" />
      <path d="M12 12l8-4.5" />
      <path d="M12 12v9" />
      <path d="M12 12L4 7.5" />
    </template>
    <template v-else-if="name === 'converter'">
      <path d="M16 3h5v5" />
      <path d="M8 3H3v5" />
      <path d="M12 12l9-9" />
      <path d="M12 12L3 21" />
      <path d="M21 16v5h-5" />
      <path d="M3 16v5h5" />
    </template>
    <template v-else-if="name === 'servers'">
      <rect x="3" y="4" width="18" height="6" rx="1" />
      <rect x="3" y="14" width="18" height="6" rx="1" />
      <circle cx="7" cy="7" r="1" fill="currentColor" stroke="none" />
      <circle cx="7" cy="17" r="1" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'apiKeys'">
      <path d="M15.5 7.5a3.5 3.5 0 1 0-5.8 2.6L4 16v4h4l5.7-5.7A3.5 3.5 0 0 0 15.5 7.5z" />
      <path d="M14 6l4 4" />
    </template>
    <template v-else-if="name === 'packages'">
      <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" />
      <path d="M12 12l8-4.5" />
      <path d="M12 12v9" />
      <path d="M12 12L4 7.5" />
      <path d="M12 3v9" />
    </template>
    <template v-else-if="name === 'menu'">
      <path d="M4 6h16" />
      <path d="M4 12h16" />
      <path d="M4 18h16" />
    </template>
    <template v-else-if="name === 'bell'">
      <path d="M15 17h5l-1.4-4.2A2 2 0 0 0 16.6 11H7.4a2 2 0 0 0-1.9 1.8L4 17h5" />
      <path d="M9 17v1a3 3 0 0 0 6 0v-1" />
    </template>
    <template v-else-if="name === 'tag'">
      <path d="M7 7h.01" />
      <path d="M7 3h5c.5 0 1 .2 1.4.6l7 7a2 2 0 0 1 0 2.8l-7 7a2 2 0 0 1-2.8 0l-7-7A2 2 0 0 1 3 12V7a4 4 0 0 1 4-4z" />
    </template>
    <template v-else-if="name === 'close'">
      <path d="M18 6L6 18" />
      <path d="M6 6l12 12" />
    </template>
    <template v-else-if="name === 'refresh'">
      <path d="M20 11a8.1 8.1 0 0 0-15.5-2m-.5-4v4h4" />
      <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
    </template>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: {
    type: String,
    required: true
  },
  class: {
    type: String,
    default: ''
  }
})

const iconClass = computed(() => props.class || 'h-4 w-4 shrink-0')
</script>
