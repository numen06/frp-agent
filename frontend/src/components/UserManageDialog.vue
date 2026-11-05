<template>
  <Dialog
    v-if="visible"
    :open="true"
    @update:open="
      (open) => {
        if (!open) {
          close();
        }
      }
    "
    ><DialogContent class="sm:max-w-lg" :aria-describedby="undefined"
      ><DialogHeader
        ><DialogTitle>{{
          forceMode ? "强制修改密码" : "用户管理"
        }}</DialogTitle></DialogHeader
      >
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <div
          v-if="forceMode"
          class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800"
          role="alert"
        >
          <p class="mb-1 font-semibold">安全提示</p>
          <div class="text-sm">
            {{
              forceReason ||
              "检测到您使用的是默认密码，为了账户安全，请立即修改密码。修改完成后才能继续使用系统。"
            }}
          </div>
        </div>
        <div
          v-if="!forceMode"
          class="mb-4 overflow-hidden rounded-xl border border-gray-200 bg-gray-50/50"
        >
          <div class="border-b border-gray-200 bg-white px-4 py-3">
            <h3>账号信息</h3>
          </div>
          <div class="px-4 py-3">
            <div class="text-xs text-gray-500">用户名</div>
            <div class="mt-0.5 font-semibold text-gray-900">
              {{ userSettings.username }}
            </div>
          </div>
        </div>
        <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div class="border-b border-gray-200 px-4 py-3">
            <h3>修改密码</h3>
          </div>
          <div class="px-4 py-4">
            <form
              id="user-password-form"
              @submit.prevent="handleChangePassword"
              class="space-y-4"
            >
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700"
                  >当前密码 <span class="text-red-600">*</span></label
                ><Input
                  type="password"
                  class="block w-full"
                  v-model="passwordForm.old_password"
                  required
                ></Input>
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700"
                  >新密码 <span class="text-red-600">*</span></label
                ><Input
                  type="password"
                  class="block w-full"
                  v-model="passwordForm.new_password"
                  required
                  minlength="6"
                ></Input
                ><small class="mt-1 block text-xs text-gray-500"
                  >密码长度至少 6 位</small
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700"
                  >确认新密码 <span class="text-red-600">*</span></label
                ><Input
                  type="password"
                  class="block w-full"
                  v-model="passwordForm.confirm_password"
                  required
                ></Input>
              </div>
            </form>
          </div>
        </div>
        <div
          class="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900"
          role="alert"
        >
          <p class="mb-2 font-semibold">注意事项</p>
          <ul
            class="mb-0 list-inside list-disc space-y-1 text-sm text-amber-900/90"
          >
            <li>修改密码后需要重新登录</li>
            <li>请妥善保管新密码，避免泄露</li>
            <li>建议使用强密码（包含字母、数字和特殊字符）</li>
          </ul>
        </div>
      </div>
      <DialogFooter
        ><Button
          type="button"
          class="w-full sm:mr-auto sm:w-auto"
          @click.prevent.stop="close"
          variant="outline"
          size="default"
        >
          取消 </Button
        ><Button
          type="submit"
          form="user-password-form"
          class="w-full sm:w-auto"
          variant="default"
          size="default"
        >
          保存修改
        </Button></DialogFooter
      ></DialogContent
    ></Dialog
  >
</template>

<script setup>
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { notify } from "@/composables/useFeedback";
import { ref, reactive, watch, computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { settingsApi } from "@/api/settings";

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  forceMode: {
    type: Boolean,
    default: false,
  },
  forceReason: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["update:show", "cancel-force"]);

const router = useRouter();
const authStore = useAuthStore();
const localHidden = ref(false);

const userSettings = reactive({
  username: "",
});

const passwordForm = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

watch(
  () => props.show,
  async (newVal) => {
    if (newVal) {
      localHidden.value = false;
      await loadUserSettings();
      passwordForm.old_password = "";
      passwordForm.new_password = "";
      passwordForm.confirm_password = "";
    }
  },
);

const visible = computed(() => props.show && !localHidden.value);

const loadUserSettings = async () => {
  try {
    const settings = await settingsApi.getUserSettings();
    userSettings.username = settings.username || authStore.username;
  } catch (error) {
    notify("加载用户设置失败: " + error.message);
  }
};

const handleChangePassword = async () => {
  if (
    !passwordForm.old_password ||
    !passwordForm.new_password ||
    !passwordForm.confirm_password
  ) {
    notify("请填写所有字段");
    return;
  }

  if (passwordForm.new_password.length < 6) {
    notify("新密码长度至少 6 位");
    return;
  }

  if (passwordForm.new_password !== passwordForm.confirm_password) {
    notify("两次输入的新密码不一致");
    return;
  }

  try {
    await settingsApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    });

    if (props.forceMode) {
      notify("密码修改成功！请重新登录");
      router.replace({ query: {} });
    } else {
      notify("密码修改成功，请重新登录");
    }

    authStore.logout();
    router.push("/login");
  } catch (error) {
    notify("修改失败: " + error.message);
  }
};

const close = () => {
  localHidden.value = true;
  if (props.forceMode) {
    emit("cancel-force");
    router.replace({ query: {} });
  }
  emit("update:show", false);
};

const showRef = computed(() => visible.value);
</script>
