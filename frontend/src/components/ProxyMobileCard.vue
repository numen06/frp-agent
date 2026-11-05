<script setup>
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import ActionMenu from "@/components/ActionMenu.vue";
import ProxyTraffic from "@/components/ProxyTraffic.vue";

defineProps({
  proxy: { type: Object, required: true },
  selectable: Boolean,
  selected: Boolean,
  groupLink: Boolean,
  canUpgrade: Boolean,
});
const emit = defineEmits(["toggle", "group", "edit", "upgrade", "delete"]);
</script>

<template>
  <article
    :data-proxy-id="proxy.id"
    class="flex h-[22rem] min-w-0 shrink-0 flex-col gap-3 rounded-xl border bg-card p-4"
    :class="selected ? 'border-primary bg-primary/5' : ''"
  >
    <div class="flex min-w-0 items-start gap-2">
      <label
        v-if="selectable"
        class="flex size-11 shrink-0 cursor-pointer items-center justify-center"
      >
        <Checkbox
          :model-value="selected"
          :aria-label="`选择代理 ${proxy.name}`"
          @update:model-value="emit('toggle')"
        />
      </label>
      <h3
        class="line-clamp-2 min-h-10 min-w-0 flex-1 break-all text-sm font-semibold leading-5"
        :title="proxy.name"
      >
        {{ proxy.name }}
      </h3>
      <span
        class="shrink-0 rounded-md px-2 py-1 text-xs"
        :class="
          proxy.status === 'online'
            ? 'bg-emerald-50 text-emerald-700'
            : 'bg-muted text-muted-foreground'
        "
        >{{ proxy.status === "online" ? "在线" : "离线" }}</span
      >
    </div>
    <dl class="grid min-w-0 grid-cols-2 gap-x-3 gap-y-2 text-xs">
      <div class="min-w-0">
        <dt class="text-muted-foreground">所属分组</dt>
        <dd class="mt-1 truncate text-sm" :title="proxy.group_name">
          <a
            v-if="groupLink && proxy.group_name"
            href="#"
            class="block truncate text-primary hover:underline"
            @click.prevent="emit('group', proxy.group_name)"
            >{{ proxy.group_name }}</a
          >
          <span v-else>{{ proxy.group_name || "未分组" }}</span>
        </dd>
      </div>
      <div class="min-w-0">
        <dt class="text-muted-foreground">类型 / 客户端</dt>
        <dd
          class="mt-1 truncate text-sm"
          :title="proxy.client_version || '未知版本'"
        >
          {{ String(proxy.proxy_type || "—").toUpperCase() }} ·
          {{ proxy.client_version || "未知" }}
        </dd>
      </div>
      <div class="min-w-0">
        <dt class="text-muted-foreground">本地地址</dt>
        <dd
          class="mt-1 truncate font-mono text-xs"
          :title="`${proxy.local_ip}:${proxy.local_port || '-'}`"
        >
          {{ proxy.local_ip }}:{{ proxy.local_port || "-" }}
        </dd>
      </div>
      <div class="min-w-0">
        <dt class="text-muted-foreground">远程端口</dt>
        <dd class="mt-1 truncate font-mono text-sm">
          {{ proxy.remote_port || "-" }}
        </dd>
      </div>
    </dl>
    <div class="min-w-0 rounded-lg bg-muted/40 p-3">
      <ProxyTraffic :proxy="proxy" compact />
    </div>
    <div class="mt-auto flex items-center gap-2 border-t pt-3">
      <Button
        variant="outline"
        size="sm"
        class="flex-1"
        aria-label="编辑"
        @click="emit('edit')"
        >编辑</Button
      >
      <ActionMenu
        text="更多"
        variant="outline"
        label="代理操作"
        :items="[
          ...(canUpgrade ? [{ action: 'upgrade', label: '客户端升级' }] : []),
          { action: 'delete', label: '删除代理', danger: true },
        ]"
        @select="(action) => emit(action === 'upgrade' ? 'upgrade' : 'delete')"
      />
    </div>
  </article>
</template>
