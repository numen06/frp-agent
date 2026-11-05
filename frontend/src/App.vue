<template>
  <TooltipProvider :delay-duration="200">
    <router-view />
    <FeedbackHost />
  </TooltipProvider>
</template>

<script setup>
import FeedbackHost from "@/components/FeedbackHost.vue";
import { TooltipProvider } from "@/components/ui/tooltip";
</script>
