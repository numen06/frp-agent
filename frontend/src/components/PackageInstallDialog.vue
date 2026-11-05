<template>
  <Dialog
    v-if="visible"
    :open="true"
    @update:open="
      (open) => {
        if (!open) {
          closeDialog();
        }
      }
    "
    ><DialogContent class="sm:max-w-4xl" :aria-describedby="undefined"
      ><DialogHeader><DialogTitle>一键脚本生成</DialogTitle></DialogHeader>
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <div class="grid gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >安装包</label
            ><ResourceCombobox
              v-model="packageId"
              label="选择安装包"
              :fetch-options="packagesApi.list"
              :get-label="
                (item) =>
                  `${item.version} / ${item.platform} / ${item.filename}`
              "
              :resolve-option="
                (id) => props.packages.find((item) => item.id === id)
              "
            />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >API Key</label
            ><ResourceCombobox
              v-model="selectedKeyId"
              label="选择 API Key"
              :fetch-options="
                (params) => apiKeysApi.list({ ...params, available_only: true })
              "
              :resolve-option="apiKeysApi.get"
            /><Input
              v-if="!selectedKeyId"
              v-model="manualApiKey"
              class="block w-full"
              type="text"
              placeholder="没有可用的 API Key，请手动输入"
            ></Input>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >安装路径</label
            ><Input
              v-model="installPath"
              class="block w-full"
              type="text"
            ></Input>
          </div>
          <div v-if="activeTab === 'install'">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >配置URL（可选）</label
            ><Input
              v-model="configUrl"
              class="block w-full"
              type="text"
              placeholder="http://.../frpc.toml"
            ></Input>
          </div>
          <ToggleGroup
            type="single"
            :model-value="activeTab"
            @update:model-value="
              (value) => {
                if (value) activeTab = value;
              }
            "
            variant="outline"
            class="flex w-full flex-wrap justify-start"
            ><ToggleGroupItem :disabled="loading" :value="'install'">
              安装脚本 </ToggleGroupItem
            ><ToggleGroupItem :disabled="loading" :value="'upgrade'">
              升级脚本
            </ToggleGroupItem></ToggleGroup
          >
          <div v-if="activeTab === 'install' && script">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >安装脚本预览</label
            ><CodeEditor
              :model-value="script"
              language="shell"
              :height="'320px'"
              :readonly="true"
            /><Button
              type="button"
              class="mt-2"
              :disabled="!packageId"
              @click="handleCopyCommand($event)"
              variant="outline"
              size="sm"
            >
              复制安装命令
            </Button>
          </div>
          <div v-if="activeTab === 'upgrade' && upgradeScript">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >升级脚本预览</label
            ><CodeEditor
              :model-value="upgradeScript"
              language="shell"
              :height="'320px'"
              :readonly="true"
            /><Button
              type="button"
              class="mt-2"
              :disabled="!packageId"
              @click="handleCopyUpgradeCommand($event)"
              variant="outline"
              size="sm"
            >
              复制升级命令
            </Button>
          </div>
        </div>
      </div>
      <DialogFooter
        ><Button
          v-if="activeTab === 'install'"
          type="button"
          :disabled="loading"
          @click="submit"
          variant="default"
          size="default"
          >{{ loading ? "生成中..." : "生成安装脚本" }}</Button
        ><Button
          v-else
          type="button"
          :disabled="loading"
          @click="submitUpgrade"
          variant="default"
          size="default"
          >{{ loading ? "生成中..." : "生成升级脚本" }}</Button
        ></DialogFooter
      ></DialogContent
    ></Dialog
  >
</template>

<script setup>
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
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
import { apiKeysApi } from "@/api/apiKeys";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import { ref, watch, computed } from "vue";
import { useApiKeysStore } from "@/stores/apiKeys";
import { packagesApi } from "@/api/packages";
import { copyText } from "@/composables/useClipboard";
import CodeEditor from "@/components/CodeEditor.vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  packages: { type: Array, default: () => [] },
  /** 与「版本」筛选中的「最新」一致，用于默认选中对应安装包 */
  latestVersion: { type: String, default: "" },
  loading: { type: Boolean, default: false },
  script: { type: String, default: "" },
  upgradeScript: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "submit", "submit-upgrade"]);
const apiKeysStore = useApiKeysStore();
const visible = ref(false);
const packageId = ref(0);
const installPath = ref("/opt/frp");
const configUrl = ref("");
const selectedKeyId = ref(0);
const manualApiKey = ref("");
const activeTab = ref("install");

const availableKeys = computed(() => {
  return apiKeysStore.availableKeys;
});

const resolveApiKey = async () => {
  if (availableKeys.value.length === 0) {
    return manualApiKey.value.trim();
  }
  const id = selectedKeyId.value;
  if (!id) return "";
  const selectedFullKey = await apiKeysStore.resolveFullKey(id);
  if (selectedFullKey) {
    return selectedFullKey;
  }

  // 兜底：若当前选中的默认 Key 无法恢复完整值，则尝试其他可用默认项
  const fallbackFullKey = await apiKeysStore.resolveDefaultFullKey();
  if (fallbackFullKey) {
    selectedKeyId.value = apiKeysStore.selectedKeyId || selectedKeyId.value;
    return fallbackFullKey;
  }
  return "";
};

const pickDefaultPackageId = () => {
  const list = props.packages || [];
  if (!list.length) return 0;
  const lv = (props.latestVersion || "").trim();
  if (lv) {
    const hit = list.find((p) => p.version === lv);
    if (hit) return hit.id;
  }
  return list[0].id;
};

watch(
  () => props.modelValue,
  async (val) => {
    visible.value = val;
    if (val) {
      activeTab.value = "install";
      await apiKeysStore.loadKeys();
      const fallbackId =
        apiKeysStore.selectedKeyId || (availableKeys.value[0]?.id ?? 0);
      selectedKeyId.value = fallbackId;
      if (fallbackId) {
        apiKeysStore.setDefaultKey(fallbackId);
      }
      manualApiKey.value = "";
      packageId.value = pickDefaultPackageId();
    }
  },
);

watch(
  () => [visible.value, props.packages, props.latestVersion],
  () => {
    if (!visible.value) return;
    const list = props.packages || [];
    if (!list.length) {
      packageId.value = 0;
      return;
    }
    if (!packageId.value || !list.some((p) => p.id === packageId.value)) {
      packageId.value = pickDefaultPackageId();
    }
  },
  { deep: true },
);

watch(visible, (val) => emit("update:modelValue", val));
watch(selectedKeyId, (id) => {
  if (id) {
    apiKeysStore.setDefaultKey(id);
  }
});

const closeDialog = () => {
  visible.value = false;
};

const submit = async () => {
  if (!packageId.value) {
    notify("请选择安装包");
    return;
  }
  if (availableKeys.value.length > 0 && !selectedKeyId.value) {
    notify("请选择 API Key");
    return;
  }
  if (availableKeys.value.length === 0 && !manualApiKey.value.trim()) {
    notify("请输入 API Key（安装脚本中的下载链接需要 API Key 认证）");
    return;
  }
  const apiKey = await resolveApiKey();
  if (!apiKey) {
    notify(
      '未能获取有效的 API Key，请到"密钥管理"页重新复制/设置默认 APPKey 后重试',
    );
    return;
  }
  emit("submit", {
    package_id: packageId.value,
    api_key: apiKey || "",
    install_path: installPath.value,
    config_url: configUrl.value,
  });
};

const handleCopyCommand = async (event) => {
  if (!packageId.value) return;
  const apiKey = await resolveApiKey();
  if (!apiKey) {
    notify(
      '未能获取有效的 API Key，请到"密钥管理"页重新复制/设置默认 APPKey 后重试',
    );
    return;
  }
  const url = packagesApi.getInstallScriptUrl({
    package_id: packageId.value,
    api_key: apiKey || "",
    install_path: installPath.value,
    config_url: configUrl.value || undefined,
  });
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`;
  await copyText(cmd, event);
};

const submitUpgrade = async () => {
  if (!packageId.value) {
    notify("请选择安装包");
    return;
  }
  if (availableKeys.value.length > 0 && !selectedKeyId.value) {
    notify("请选择 API Key");
    return;
  }
  if (availableKeys.value.length === 0 && !manualApiKey.value.trim()) {
    notify("请输入 API Key（升级脚本中的下载链接需要 API Key 认证）");
    return;
  }
  const apiKey = await resolveApiKey();
  if (!apiKey) {
    notify(
      '未能获取有效的 API Key，请到"密钥管理"页重新复制/设置默认 APPKey 后重试',
    );
    return;
  }
  emit("submit-upgrade", {
    package_id: packageId.value,
    api_key: apiKey || "",
    install_path: installPath.value,
  });
};

const handleCopyUpgradeCommand = async (event) => {
  if (!packageId.value) return;
  const apiKey = await resolveApiKey();
  if (!apiKey) {
    notify(
      '未能获取有效的 API Key，请到"密钥管理"页重新复制/设置默认 APPKey 后重试',
    );
    return;
  }
  const url = packagesApi.getUpgradeScriptUrl({
    package_id: packageId.value,
    api_key: apiKey || "",
    install_path: installPath.value,
  });
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`;
  await copyText(cmd, event);
};
</script>
