<template>
  <div class="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
    <div class="flex flex-wrap items-end gap-2">
      <div class="min-w-[140px] flex-1">
        <label class="mb-1 block text-xs font-medium text-gray-600">凭据</label>
        <select
          v-model.number="selectedId"
          class="block w-full rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-sm"
          @change="onSelect"
        >
          <option :value="0">请选择 SSH 凭据</option>
          <option v-for="c in credentials" :key="c.id" :value="c.id">
            {{ c.name }} ({{ c.username }})
          </option>
        </select>
      </div>
      <button
        type="button"
        class="rounded-lg border border-blue-600 px-2.5 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50"
        @click="showEditor = !showEditor"
      >
        {{ showEditor ? '收起' : editingId ? '编辑凭据' : '新建凭据' }}
      </button>
    </div>

    <div v-if="showEditor" class="space-y-2 border-t border-gray-200 pt-3">
      <div class="grid gap-2 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-600">名称</label>
          <input v-model="form.name" type="text" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm" />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-600">用户名</label>
          <input v-model="form.username" type="text" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm" />
        </div>
      </div>
      <div>
        <label class="mb-1 block text-xs font-medium text-gray-600">认证方式</label>
        <select v-model="form.auth_type" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm">
          <option value="password">密码</option>
          <option value="private_key">私钥</option>
        </select>
      </div>
      <div v-if="form.auth_type === 'password'">
        <label class="mb-1 block text-xs font-medium text-gray-600">
          密码 {{ editingId ? '（留空不修改）' : '' }}
        </label>
        <input v-model="form.password" type="password" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm" />
      </div>
      <template v-else>
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-600">
            私钥 {{ editingId ? '（留空不修改）' : '' }}
          </label>
          <textarea
            v-model="form.private_key"
            rows="4"
            class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 font-mono text-xs"
            placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-600">私钥口令（可选）</label>
          <input v-model="form.passphrase" type="password" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm" />
        </div>
      </template>
      <div class="flex gap-2">
        <button
          type="button"
          class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          :disabled="saving"
          @click="saveCredential"
        >
          {{ saving ? '保存中...' : '保存凭据' }}
        </button>
        <button
          v-if="editingId"
          type="button"
          class="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
          @click="deleteCredential"
        >
          删除
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { sshCredentialsApi } from '@/api/sshCredentials'

const props = defineProps({
  modelValue: { type: Number, default: 0 }
})

const emit = defineEmits(['update:modelValue'])

const credentials = ref([])
const selectedId = ref(props.modelValue || 0)
const showEditor = ref(false)
const saving = ref(false)
const editingId = ref(null)

const form = ref({
  name: '',
  username: 'root',
  auth_type: 'password',
  password: '',
  private_key: '',
  passphrase: ''
})

watch(() => props.modelValue, (v) => {
  selectedId.value = v || 0
})

function resetForm() {
  form.value = {
    name: '',
    username: 'root',
    auth_type: 'password',
    password: '',
    private_key: '',
    passphrase: ''
  }
  editingId.value = null
}

async function loadCredentials() {
  try {
    credentials.value = await sshCredentialsApi.list()
  } catch (e) {
    console.error(e)
  }
}

function onSelect() {
  emit('update:modelValue', selectedId.value)
  const c = credentials.value.find((x) => x.id === selectedId.value)
  if (c) {
    editingId.value = c.id
    form.value.name = c.name
    form.value.username = c.username
    form.value.auth_type = c.auth_type
    form.value.password = ''
    form.value.private_key = ''
    form.value.passphrase = ''
  }
}

async function saveCredential() {
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      username: form.value.username,
      auth_type: form.value.auth_type
    }
    if (form.value.auth_type === 'password' && form.value.password) {
      payload.password = form.value.password
    }
    if (form.value.auth_type === 'private_key') {
      if (form.value.private_key) payload.private_key = form.value.private_key
      if (form.value.passphrase) payload.passphrase = form.value.passphrase
    }
    if (editingId.value) {
      await sshCredentialsApi.update(editingId.value, payload)
    } else {
      if (form.value.auth_type === 'password' && !form.value.password) {
        throw new Error('请填写密码')
      }
      if (form.value.auth_type === 'private_key' && !form.value.private_key) {
        throw new Error('请填写私钥')
      }
      const created = await sshCredentialsApi.create({
        ...payload,
        password: form.value.password,
        private_key: form.value.private_key,
        passphrase: form.value.passphrase || undefined
      })
      selectedId.value = created.id
      emit('update:modelValue', created.id)
    }
    await loadCredentials()
    showEditor.value = false
    resetForm()
  } catch (e) {
    alert(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteCredential() {
  if (!editingId.value || !confirm('确定删除该 SSH 凭据？')) return
  try {
    await sshCredentialsApi.remove(editingId.value)
    if (selectedId.value === editingId.value) {
      selectedId.value = 0
      emit('update:modelValue', 0)
    }
    await loadCredentials()
    resetForm()
    showEditor.value = false
  } catch (e) {
    alert(e.message || '删除失败')
  }
}

onMounted(loadCredentials)

defineExpose({ loadCredentials })
</script>
