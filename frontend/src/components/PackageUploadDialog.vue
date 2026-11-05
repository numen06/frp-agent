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
      ><DialogHeader><DialogTitle>上传安装包</DialogTitle></DialogHeader>
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >选择文件（支持多选）</label
          >
          <div
            v-bind="getRootProps()"
            class="flex min-h-34 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-6 text-center text-sm text-gray-600 transition-colors hover:border-blue-400 hover:bg-blue-50/40"
            :class="{
              'border-blue-500 bg-blue-50/60': isDragActive,
              'border-red-400 bg-red-50/50': isDragReject,
              'border-green-400 bg-green-50/50':
                fileList.length > 0 && !isDragActive && !isDragReject,
            }"
          >
            <Input v-bind="getInputProps()"></Input
            ><template v-if="fileList.length === 0">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-8 w-8 text-gray-400"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                stroke-width="2"
                stroke="currentColor"
                fill="none"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                <path
                  d="M17 21H7a2 2 0 0 1 -2 -2V5a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"
                />
                <path d="M12 11l0 6" />
                <path d="M9.5 13.5l2.5 -2.5l2.5 2.5" /></svg
              ><span v-if="isDragReject" class="font-medium text-red-500"
                >不支持该文件类型</span
              ><span v-else>拖拽文件到此处，或点击选择文件</span
              ><span class="text-xs text-gray-500"
                >支持批量选择多个安装包（.zip, .gz, .tgz, .xz）</span
              ><span class="text-xs text-gray-500"
                >官方包名如 frp_0.61.1_linux_amd64.tar.gz
                将自动解析版本与平台</span
              > </template
            ><template v-else>
              <span class="font-medium text-green-700"
                >已选择 {{ fileList.length }} 个文件</span
              ><span class="text-xs text-gray-500"
                >点击或拖拽可继续添加文件</span
              >
            </template>
          </div>
          <p
            v-if="fileRejections.length"
            class="mb-0 mt-1 text-xs text-red-600"
          >
            {{
              fileRejections
                .map(
                  (r) =>
                    `${r.file.name}: ${r.errors.map((e) => e.message).join(", ")}`,
                )
                .join("; ")
            }}
          </p>
        </div>
        <div v-if="fileList.length > 0" class="mb-4">
          <div class="mb-2 flex items-center justify-between">
            <label class="mb-0 text-sm font-medium text-gray-700"
              >文件列表</label
            ><Button
              type="button"
              class="inline-flex items-center gap-1 text-xs font-medium text-red-600"
              @click="clearAll"
              variant="ghost"
              size="default"
              ><svg
                xmlns="http://www.w3.org/2000/svg"
                class="inline-block h-4 w-4 align-text-bottom"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                stroke-width="2"
                stroke="currentColor"
                fill="none"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M4 7l16 0" />
                <path d="M10 11l0 6" />
                <path d="M14 11l0 6" />
                <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12" />
                <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3" />
              </svg>
              清空
            </Button>
          </div>
          <div
            class="max-h-72 overflow-y-auto rounded-lg border border-gray-200"
          >
            <Table class="w-full text-left"
              ><TableHeader
                ><TableRow
                  ><TableHead>文件名</TableHead
                  ><TableHead class="w-20 text-center">大小</TableHead
                  ><TableHead class="w-24 text-center">版本</TableHead
                  ><TableHead class="w-36 text-center">平台</TableHead
                  ><TableHead class="w-10"></TableHead></TableRow></TableHeader
              ><TableBody
                ><TableRow
                  v-for="(item, idx) in uploadPage.items.value"
                  :key="item.id"
                  ><TableCell
                    ><div
                      class="truncate font-medium text-gray-900"
                      :title="item.file.name"
                    >
                      {{ item.file.name }}
                    </div>
                    <div
                      v-if="!item.parsed"
                      class="mt-0.5 text-xs text-red-600"
                    >
                      无法自动解析版本/平台
                    </div></TableCell
                  ><TableCell class="whitespace-nowrap text-center">{{
                    formatSize(item.file.size)
                  }}</TableCell
                  ><TableCell class="text-center"
                    ><span
                      v-if="item.parsed"
                      class="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-[0.7rem] font-medium text-blue-800"
                      >{{ item.parsed.version }}</span
                    ><span v-else class="text-gray-400">-</span></TableCell
                  ><TableCell class="text-center"
                    ><span
                      v-if="item.parsed"
                      class="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-[0.7rem] font-medium text-green-800"
                      >{{ item.parsed.platform }}</span
                    ><span v-else class="text-gray-400">-</span></TableCell
                  ><TableCell class="text-center"
                    ><Button
                      type="button"
                      class="inline-flex shrink-0 items-center justify-center transition-colors hover:text-red-500"
                      title="移除"
                      @click="removeFile(item.id)"
                      variant="ghost"
                      size="default"
                      aria-label="移除"
                      ><svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-4 w-4"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        stroke-width="2"
                        stroke="currentColor"
                        fill="none"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M18 6l-12 12" />
                        <path
                          d="M6 6l12 12"
                        /></svg></Button></TableCell></TableRow></TableBody
            ></Table>
            <div class="p-3">
              <TablePagination
                :total="uploadPage.pagination.total"
                :page="uploadPage.pagination.page"
                :page-size="uploadPage.pagination.page_size"
                @page-change="uploadPage.load"
                @page-size-change="uploadPage.resize"
              />
            </div>
          </div>
        </div>
        <template v-if="fileList.length === 1">
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >版本</label
            ><Input
              v-model="manualVersion"
              class="block w-full"
              type="text"
              placeholder="例如 v0.61.1（可选，可由文件名识别）"
            ></Input>
          </div>
          <div class="mb-0">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >平台</label
            ><Select v-model="manualPlatform"
              ><SelectTrigger class="w-full" aria-label="平台"
                ><SelectValue
                  placeholder="请选择或自动识别"
                ></SelectValue></SelectTrigger
              ><SelectContent
                ><SelectItem :value="null">请选择或自动识别</SelectItem
                ><SelectItem v-for="p in props.platforms" :key="p" :value="p">{{
                  p
                }}</SelectItem></SelectContent
              ></Select
            >
            <p
              v-if="fileList[0]?.parsed"
              class="mb-0 mt-1 text-xs text-gray-500"
            >
              已根据文件名填入，可自行修改。
            </p>
          </div>
        </template>
        <div
          v-if="unparsedCount > 0"
          class="mb-0 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
        >
          <strong>注意：</strong>{{ unparsedCount }}
          个文件无法从文件名自动解析版本/平台，批量上传时将跳过这些文件。
          <template v-if="unparsedNames.length > 0">
            <br /><span class="text-gray-600">{{
              unparsedNames.join("、")
            }}</span>
          </template>
        </div>
      </div>
      <DialogFooter
        ><Button
          type="button"
          class="w-full sm:mr-auto sm:w-auto"
          @click="closeDialog"
          variant="outline"
          size="default"
          >取消</Button
        ><Button
          v-if="fileList.length === 1"
          type="button"
          class="w-full sm:w-auto"
          :disabled="
            loading ||
            fileList.length === 0 ||
            (!manualVersion && !manualPlatform)
          "
          @click="submit"
          variant="default"
          size="default"
          >{{ loading ? "上传中..." : "上传" }}</Button
        ><Button
          v-else
          type="button"
          class="w-full sm:w-auto"
          :disabled="loading || fileList.length === 0 || parsedCount === 0"
          @click="submit"
          variant="default"
          size="default"
          >{{
            loading
              ? "上传中..."
              : `批量上传 (${parsedCount}/${fileList.length} 个文件)`
          }}</Button
        ></DialogFooter
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
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import TablePagination from "@/components/TablePagination.vue";
import { useLocalPagination } from "@/composables/useLocalPagination";
import { ref, watch, computed } from "vue";
import { useDropzone } from "vue3-dropzone";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  platforms: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue", "submit", "submit-batch"]);

const visible = ref(false);
const fileList = ref([]);
const uploadPage = useLocalPagination(fileList);
const manualVersion = ref("");
const manualPlatform = ref("");

let fileIdCounter = 0;
function makeId() {
  return ++fileIdCounter;
}

function parseFilename(filename) {
  if (!filename) return null;
  const re = /^frp_(\d+\.\d+\.\d+)_(.+)\.(?:tar\.gz|tgz|zip|tar\.xz)$/i;
  const m = filename.match(re);
  if (!m) return null;
  return { version: `v${m[1]}`, platform: m[2] };
}

function formatSize(bytes) {
  if (!bytes || bytes < 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const onDropAccepted = (files) => {
  for (const f of files) {
    const parsed = parseFilename(f.name);
    fileList.value.push({ file: f, parsed, id: makeId() });
  }
  if (fileList.value.length === 1) {
    const first = fileList.value[0];
    if (first.parsed) {
      manualVersion.value = first.parsed.version;
      manualPlatform.value = first.parsed.platform;
    }
  }
};

const {
  getRootProps,
  getInputProps,
  isDragActive,
  isDragReject,
  fileRejections,
} = useDropzone({
  accept: ".zip,.gz,.tgz,.xz",
  multiple: true,
  noClick: false,
  noDrag: false,
  onDropAccepted,
});

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
  },
);
watch(visible, (val) => emit("update:modelValue", val));

watch(visible, (open) => {
  if (!open) {
    fileList.value = [];
    manualVersion.value = "";
    manualPlatform.value = "";
    fileIdCounter = 0;
  }
});

const closeDialog = () => {
  visible.value = false;
};

const removeFile = (id) => {
  const index = fileList.value.findIndex((item) => item.id === id);
  if (index >= 0) fileList.value.splice(index, 1);
  if (fileList.value.length === 1) {
    const first = fileList.value[0];
    if (first.parsed) {
      manualVersion.value = first.parsed.version;
      manualPlatform.value = first.parsed.platform;
    }
  } else if (fileList.value.length === 0) {
    manualVersion.value = "";
    manualPlatform.value = "";
  }
};

const clearAll = () => {
  fileList.value = [];
  manualVersion.value = "";
  manualPlatform.value = "";
};

const parsedCount = computed(
  () => fileList.value.filter((i) => i.parsed).length,
);
const unparsedCount = computed(
  () => fileList.value.filter((i) => !i.parsed).length,
);
const unparsedNames = computed(() =>
  fileList.value.filter((i) => !i.parsed).map((i) => i.file.name),
);

const submit = () => {
  if (fileList.value.length === 0) return;
  if (fileList.value.length === 1) {
    const item = fileList.value[0];
    emit("submit", {
      version: manualVersion.value?.trim() || "",
      platform: manualPlatform.value?.trim() || "",
      file: item.file,
    });
  } else {
    const parsedFiles = fileList.value.filter((i) => i.parsed);
    if (parsedFiles.length === 0) return;
    emit("submit-batch", { files: parsedFiles.map((i) => i.file) });
  }
};
</script>
