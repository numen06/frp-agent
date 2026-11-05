<template>
  <div
    class="space-y-1 text-xs text-gray-600"
    title="FRP 服务端统计：入站/出站按 frps 方向，流量为采集时 frps 当日计数；重启可能清零。连接数为采集时快照。"
  >
    <template v-if="compact">
      <dl class="grid min-w-0 grid-cols-3 gap-2">
        <div class="min-w-0">
          <dt class="text-muted-foreground">入站</dt>
          <dd class="mt-1 truncate font-medium text-foreground">
            {{ formatBytes(proxy.today_traffic_in) }}
          </dd>
        </div>
        <div class="min-w-0">
          <dt class="text-muted-foreground">出站</dt>
          <dd class="mt-1 truncate font-medium text-foreground">
            {{ formatBytes(proxy.today_traffic_out) }}
          </dd>
        </div>
        <div class="min-w-0">
          <dt class="text-muted-foreground">连接</dt>
          <dd class="mt-1 truncate font-medium text-foreground">
            {{ proxy.cur_conns ?? "未采集" }}
          </dd>
        </div>
      </dl>
    </template>
    <template v-else
      ><p class="whitespace-nowrap">
        入 {{ formatBytes(proxy.today_traffic_in) }} · 出
        {{ formatBytes(proxy.today_traffic_out) }}
      </p>
      <p>连接 {{ proxy.cur_conns ?? "未采集" }}</p></template
    >
    <p
      v-if="proxy.traffic_updated_at"
      class="truncate text-gray-400"
      :title="sampledAt"
    >
      采集 {{ sampledAt }}
    </p>
    <p v-else class="text-gray-400">同步后更新</p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { formatBytes } from "@/utils/traffic";
const props = defineProps({
  proxy: { type: Object, required: true },
  compact: Boolean,
});
const sampledAt = computed(() => {
  const value = props.proxy.traffic_updated_at;
  if (!value) return "";
  return new Date(
    /[Zz]$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`,
  ).toLocaleString("zh-CN");
});
</script>
