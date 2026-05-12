<template>
  <div>
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="border-b border-gray-200 px-5 py-3.5">
        <h3 class="text-base font-semibold text-gray-900">INI 转 TOML 工具</h3>
      </div>
      <div class="p-5">
        <IniConverter />
      </div>
    </div>
  </div>
</template>

<script setup>
import IniConverter from '@/components/IniConverter.vue'
</script>

