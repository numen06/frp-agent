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
    ><DialogContent class="sm:max-w-lg" :aria-describedby="undefined"
      ><DialogHeader
        ><DialogTitle>从 GitHub 同步安装包</DialogTitle></DialogHeader
      >
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >版本</label
          ><Select v-model="form.version"
            ><SelectTrigger class="w-full" aria-label="版本"
              ><SelectValue
                placeholder="请选择版本"
              ></SelectValue></SelectTrigger
            ><SelectContent
              ><SelectItem :value="null">请选择版本</SelectItem
              ><SelectItem
                v-for="item in releases"
                :key="item.version"
                :value="item.version"
                >{{ item.version }}</SelectItem
              ></SelectContent
            ></Select
          >
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >下载通道</label
          ><ToggleGroup
            type="single"
            :model-value="form.download_source"
            @update:model-value="
              (value) => {
                if (value) form.download_source = value;
              }
            "
            variant="outline"
            class="flex w-full flex-wrap justify-start"
            ><ToggleGroupItem :value="'origin'"> 源地址 </ToggleGroupItem
            ><ToggleGroupItem :value="'accelerated'">
              国内加速下载
            </ToggleGroupItem></ToggleGroup
          >
        </div>
        <div class="mb-0">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >平台（可多选）</label
          >
          <div
            v-if="platformsForVersion.length"
            class="mb-2 flex flex-wrap items-center gap-2"
          >
            <Button
              type="button"
              class="inline-flex items-center justify-center text-xs font-medium transition-colors"
              @click="selectAll"
              variant="ghost"
              size="default"
            >
              全选 </Button
            ><Button
              type="button"
              class="inline-flex items-center justify-center text-xs font-medium transition-colors"
              @click="deselectAll"
              variant="ghost"
              size="default"
            >
              取消全选 </Button
            ><Button
              type="button"
              class="inline-flex items-center justify-center text-xs font-medium transition-colors"
              @click="invertSelection"
              variant="ghost"
              size="default"
            >
              反选 </Button
            ><span class="ml-auto text-xs font-medium text-gray-600"
              >已选 {{ form.platforms.length }} /
              {{ platformsForVersion.length }}</span
            >
          </div>
          <div class="grid max-h-[260px] gap-2 overflow-y-auto">
            <label
              v-for="p in platformsForVersion"
              :key="p"
              class="flex cursor-pointer items-center gap-2 rounded-lg border border-gray-100 px-2 py-1.5 hover:bg-gray-50"
            >
              <Checkbox
                class="w-4"
                :model-value="form.platforms.includes(p)"
                @update:model-value="
                  (checked) => {
                    form.platforms = checked
                      ? [...form.platforms, p]
                      : form.platforms.filter((value) => value !== p);
                  }
                "
              ></Checkbox
              ><span class="text-sm text-gray-800">{{ p }}</span>
            </label>
          </div>
        </div>
      </div>
      <DialogFooter>
        后台下载中… {{ progress.completed }} / {{ progress.total }}
        <span v-if="progress.status === 'running'" class="ml-1"
          >（可关闭此窗口，任务仍在继续）</span
        ></DialogFooter
      ><DialogFooter
        ><Button
          type="button"
          class="w-full sm:mr-auto sm:w-auto"
          @click="closeDialog"
          variant="outline"
          size="default"
        >
          取消 </Button
        ><Button
          type="button"
          class="w-full sm:w-auto"
          :disabled="loading"
          @click="submit"
          variant="default"
          size="default"
          >{{ syncButtonLabel }}</Button
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
import { Checkbox } from "@/components/ui/checkbox";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { notify } from "@/composables/useFeedback";
import { computed, reactive, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  releases: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  progress: {
    type: Object,
    default: () => ({ completed: 0, total: 0, status: "" }),
  },
});

const emit = defineEmits(["update:modelValue", "submit"]);
const visible = ref(false);
const form = reactive({
  version: "",
  platforms: [],
  download_source: "origin",
});

const platformsForVersion = computed(() => {
  const rel = props.releases.find((r) => r.version === form.version);
  return rel?.platforms?.length ? rel.platforms : [];
});

const syncButtonLabel = computed(() => {
  if (!props.loading) return "开始同步";
  if (props.progress.total > 0) {
    return `下载中 (${props.progress.completed}/${props.progress.total})`;
  }
  return "提交中...";
});

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
  },
);
watch(visible, (val) => emit("update:modelValue", val));

watch(
  () => [form.version, props.releases],
  () => {
    const list = platformsForVersion.value;
    form.platforms = list.length ? [...list] : [];
  },
  { deep: true },
);

const closeDialog = () => {
  visible.value = false;
};

const selectAll = () => {
  form.platforms = [...platformsForVersion.value];
};
const deselectAll = () => {
  form.platforms = [];
};
const invertSelection = () => {
  const all = platformsForVersion.value;
  form.platforms = all.filter((p) => !form.platforms.includes(p));
};

const submit = () => {
  if (!form.version) {
    notify("请选择版本");
    return;
  }
  emit("submit", {
    version: form.version,
    platforms: form.platforms,
    download_source: form.download_source,
  });
};
</script>
