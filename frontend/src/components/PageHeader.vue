<template>
  <header class="page-heading">
    <div class="min-w-0">
      <slot name="before" />
      <h1 class="page-title">{{ title }} <slot name="status" /></h1>
      <p v-if="description" class="page-description">{{ description }}</p>
    </div>
    <div v-if="$slots.default" class="page-actions"><slot /></div>
  </header>
</template>

<script setup>
defineProps({ title: { type: String, required: true }, description: String });
</script>
