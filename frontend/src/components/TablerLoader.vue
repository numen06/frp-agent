<template>
  <div class="loader" :class="{ 'loader-sm': size === 'sm' }" :style="style"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  color: {
    type: String,
    default: '#066fd1' // Tabler primary color
  }
})

const style = computed(() => ({
  color: props.color
}))
</script>

<style scoped>
.loader {
  position: relative;
  display: block;
  width: 2.5rem;
  height: 2.5rem;
  color: var(--tblr-primary, #066fd1);
  vertical-align: middle;
}

.loader-sm {
  width: 1.5rem;
  height: 1.5rem;
}

.loader:after {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  content: "";
  border: 1px var(--tblr-border-style, solid);
  border-color: transparent;
  border-top-color: currentColor;
  border-left-color: currentColor;
  border-radius: 100rem;
  animation: rotate-360 0.6s linear;
  animation-iteration-count: infinite;
}

@keyframes rotate-360 {
  to {
    transform: rotate(360deg);
  }
}
</style>

