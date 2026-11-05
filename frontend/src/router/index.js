import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { settingsApi } from "@/api/settings";
import { managedHostsApi } from "@/api/managedHosts";

async function requireHostAdmin() {
  try {
    return (await managedHostsApi.context()).is_admin || "/hosts";
  } catch {
    return "/hosts";
  }
}

async function requireAdmin() {
  try {
    return (
      (await settingsApi.getUserSettings()).role === "admin" || "/dashboard"
    );
  } catch {
    return "/dashboard";
  }
}

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/Login.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    component: () => import("@/views/Layout.vue"),
    redirect: "/dashboard",
    meta: { requiresAuth: true },
    children: [
      {
        path: "hosts/:id(\\d+)",
        name: "HostDetail",
        component: () => import("@/views/HostDetailPage.vue"),
      },
      ...[
        { path: "hosts/new", name: "HostCreate" },
        { path: "hosts/:id(\\d+)/edit", name: "HostEdit" },
        { path: "hosts/:id(\\d+)/clone", name: "HostClone" },
      ].map((route) => ({
        ...route,
        component: () => import("@/views/HostEditorPage.vue"),
        beforeEnter: requireHostAdmin,
      })),
      {
        path: "operations",
        name: "Operations",
        component: () => import("@/views/OperationsPage.vue"),
        beforeEnter: requireAdmin,
      },
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/Dashboard.vue"),
      },
      {
        path: "tunnel-services",
        name: "TunnelServices",
        component: () => import("@/views/TunnelServicesPage.vue"),
      },
      {
        path: "servers",
        redirect: (to) => ({
          path: "/tunnel-services",
          query: { ...to.query, tab: "servers" },
        }),
      },
      {
        path: "builtin-service",
        redirect: (to) => ({
          path: "/tunnel-services",
          query: { ...to.query, tab: "builtin" },
        }),
      },
      {
        path: "hosts",
        name: "HostManage",
        component: () => import("@/views/HostManagePage.vue"),
      },
      {
        path: "proxies",
        name: "ProxyList",
        component: () => import("@/views/ProxyList.vue"),
      },
      {
        path: "groups",
        name: "GroupManage",
        component: () => import("@/views/GroupManagePage.vue"),
      },
      {
        path: "converter",
        name: "IniConverter",
        component: () => import("@/views/IniConverterPage.vue"),
      },
      {
        path: "api-keys",
        name: "ApiKeys",
        component: () => import("@/views/ApiKeysPage.vue"),
      },
      {
        path: "packages",
        name: "PackageManage",
        component: () => import("@/views/PackageManagePage.vue"),
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/dashboard",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next("/login");
  } else if (to.path === "/login" && authStore.isAuthenticated) {
    // 如果已登录，检查是否需要强制修改密码
    const checkPassword = async () => {
      try {
        const axios = (await import("axios")).default;
        const token = localStorage.getItem("auth_token");

        if (token) {
          const axiosInstance = axios.create({
            baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
            timeout: 5000,
          });

          const result = await axiosInstance.get("/settings/check-password", {
            headers: { Authorization: `Basic ${token}` },
          });

          if (result.data?.require_password_change) {
            next({
              path: "/dashboard",
              query: {
                forcePasswordChange: "true",
                reason: result.data.reason,
              },
            });
            return;
          }
        }
      } catch (error) {
        // 检查失败不影响正常登录流程
        console.warn("检查密码要求失败:", error);
      }

      next("/dashboard");
    };

    checkPassword();
  } else {
    next();
  }
});

export default router;
