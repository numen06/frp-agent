<template>
  <div>
    <Card
      ><div class="border-b border-gray-200 px-3 py-3 sm:px-5 sm:py-3.5">
        <h3 class="text-base font-semibold text-gray-900">INI 转 TOML 工具</h3>
      </div>
      <CardContent><IniConverter /></CardContent
    ></Card>
  </div>
</template>

<script setup>
import { CardContent } from "@/components/ui/card";
import { Card } from "@/components/ui/card";
import IniConverter from "@/components/IniConverter.vue";
</script>
