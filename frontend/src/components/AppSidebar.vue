<script setup>
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import {
  Activity,
  ArrowLeftRight,
  Boxes,
  Folder,
  KeyRound,
  LayoutDashboard,
  Menu,
  Monitor,
  Server,
  X,
} from "@lucide/vue";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import FrpLogo from "@/components/FrpLogo.vue";

const props = defineProps({ role: String, version: String });
const route = useRoute();
const { setOpenMobile } = useSidebar();
const groups = computed(() => [
  {
    label: "工作台",
    items: [
      { path: "/dashboard", label: "仪表盘", icon: LayoutDashboard },
      ...(props.role === "admin"
        ? [{ path: "/operations", label: "运行维护", icon: Activity }]
        : []),
    ],
  },
  {
    label: "资源管理",
    items: [
      { path: "/proxies", label: "代理列表", icon: ArrowLeftRight },
      { path: "/groups", label: "分组管理", icon: Folder },
      { path: "/tunnel-services", label: "穿透服务", icon: Server },
      { path: "/machines", label: "主机资源", icon: Monitor },
    ],
  },
  {
    label: "系统工具",
    items: [
      { path: "/packages", label: "安装包管理", icon: Boxes },
      { path: "/converter", label: "配置转换", icon: Menu },
      ...(props.role === "admin"
        ? [{ path: "/api-keys", label: "密钥管理", icon: KeyRound }]
        : []),
    ],
  },
]);
const active = (path) =>
  route.path === path ||
  (path === "/machines" &&
    (route.path.startsWith("/machines/") || route.path.startsWith("/hosts")));
watch(
  () => route.fullPath,
  () => setOpenMobile(false),
);
</script>

<template>
  <Sidebar collapsible="icon">
    <SidebarHeader class="border-b px-3 py-4">
      <div class="flex items-center justify-between gap-2">
        <router-link
          to="/dashboard"
          aria-label="FRP-AGENT 首页"
          class="flex min-w-0 items-center gap-2.5 text-primary"
          @click="setOpenMobile(false)"
        >
          <FrpLogo :size="30" />
          <div class="group-data-[collapsible=icon]:hidden">
            <div class="text-sm font-semibold tracking-wide text-foreground">
              FRP-AGENT
            </div>
            <div class="mt-0.5 text-xs text-muted-foreground">
              代理与主机管理
            </div>
          </div> </router-link
        ><Button
          variant="ghost"
          size="icon"
          class="lg:hidden"
          aria-label="关闭导航菜单"
          @click="setOpenMobile(false)"
          ><X class="size-4"
        /></Button>
      </div> </SidebarHeader
    ><SidebarContent>
      <nav aria-label="主导航">
        <SidebarGroup v-for="group in groups" :key="group.label">
          <SidebarGroupLabel>{{ group.label }}</SidebarGroupLabel
          ><SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem v-for="item in group.items" :key="item.path">
                <SidebarMenuButton
                  as-child
                  :is-active="active(item.path)"
                  :tooltip="item.label"
                >
                  <router-link
                    :to="item.path"
                    :aria-current="active(item.path) ? 'page' : undefined"
                    @click="setOpenMobile(false)"
                    ><component :is="item.icon" /><span>{{
                      item.label
                    }}</span></router-link
                  >
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </nav> </SidebarContent
    ><SidebarFooter
      class="border-t px-4 py-3 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden"
      >FRP-AGENT v{{ version || "…" }}</SidebarFooter
    >
  </Sidebar>
</template>
