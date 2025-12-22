<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <p class="text-muted mb-0">管理所有代理分组，支持重命名和快速生成配置</p>
      <div class="d-flex gap-2">
        <button class="btn btn-primary btn-sm" @click="showCreateDialog = true">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M12 5l0 14" />
            <path d="M5 12l14 0" />
          </svg>
          新增分组
        </button>
        <button class="btn btn-success btn-sm" @click="handleAutoAnalyze">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
            <path d="M21 21l-6 -6" />
          </svg>
          自动分析分组
        </button>
      </div>
    </div>
    
    <div class="table-responsive">
      <table class="table table-vcenter card-table">
        <thead>
          <tr>
            <th>分组名称</th>
            <th>代理数量</th>
            <th>在线</th>
            <th>离线</th>
            <th class="w-1">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="groupsStore.loading">
            <td colspan="5" class="text-center py-4">
              <div class="spinner-border spinner-border-sm" role="status"></div>
              <span class="ms-2">加载中...</span>
            </td>
          </tr>
          <tr v-else-if="groupsStore.groups.length === 0">
            <td colspan="5" class="text-center text-muted py-4">暂无分组，请先创建分组或导入配置</td>
          </tr>
          <tr v-else v-for="group in groupsStore.groups" :key="group.group_name">
            <td>
              <strong class="text-primary">{{ group.group_name }}</strong>
            </td>
            <td>{{ group.total_count }}</td>
            <td>
              <span class="badge text-bg-success">{{ group.online_count }}</span>
            </td>
            <td>
              <span class="badge text-bg-danger">{{ group.offline_count }}</span>
            </td>
            <td>
              <div class="dropdown">
                <button class="btn btn-sm dropdown-toggle" data-bs-toggle="dropdown">
                  操作
                </button>
                <div class="dropdown-menu">
                  <a class="dropdown-item" href="#" @click.prevent="viewGroupProxies(group.group_name)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
                      <path d="M21 21l-6 -6" />
                    </svg>
                    查看代理
                  </a>
                  <a class="dropdown-item" href="#" @click.prevent="editGroup(group)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
                      <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
                      <path d="M16 5l3 3" />
                    </svg>
                    重命名
                  </a>
                  <a class="dropdown-item" href="#" @click.prevent="generateGroupConfig(group.group_name)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                      <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                    </svg>
                    生成配置
                  </a>
                  <div class="dropdown-divider"></div>
                  <a class="dropdown-item text-danger" href="#" @click.prevent="deleteGroup(group)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M4 7l16 0" />
                      <path d="M10 11l0 6" />
                      <path d="M14 11l0 6" />
                      <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12" />
                      <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3" />
                    </svg>
                    删除
                  </a>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 创建分组对话框 -->
    <div v-if="showCreateDialog" class="modal-backdrop fade show" @click="closeCreateDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: showCreateDialog, 'd-block': showCreateDialog }" tabindex="-1" role="dialog" :style="showCreateDialog ? 'display: block;' : ''" @click.self="closeCreateDialog">
      <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">新增分组</h5>
            <button type="button" class="btn-close" @click="closeCreateDialog"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">分组名称 <span class="text-danger">*</span></label>
              <input type="text" class="form-control" v-model="createForm.group_name" placeholder="例如: dlyy" required />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary me-auto" @click="closeCreateDialog">取消</button>
            <button type="button" class="btn btn-primary" @click="handleCreateGroup">创建</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 重命名分组对话框 -->
    <div v-if="showRenameDialog" class="modal-backdrop fade show" @click="closeRenameDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: showRenameDialog, 'd-block': showRenameDialog }" tabindex="-1" role="dialog" :style="showRenameDialog ? 'display: block;' : ''" @click.self="closeRenameDialog">
      <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">重命名分组</h5>
            <button type="button" class="btn-close" @click="closeRenameDialog"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">新分组名称 <span class="text-danger">*</span></label>
              <input type="text" class="form-control" v-model="renameForm.new_name" required />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary me-auto" @click="closeRenameDialog">取消</button>
            <button type="button" class="btn btn-primary" @click="handleRenameGroup">保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useGroupsStore } from '@/stores/groups'
import { useModal } from '@/composables/useModal'

const emit = defineEmits(['view-group', 'generate-config'])

const props = defineProps({
  serverId: {
    type: Number,
    required: true
  }
})

const groupsStore = useGroupsStore()

const showCreateDialog = ref(false)
const showRenameDialog = ref(false)
const currentGroup = ref(null)

const createForm = reactive({
  group_name: ''
})

const renameForm = reactive({
  new_name: ''
})

const handleCreateGroup = async () => {
  if (!createForm.group_name) {
    alert('请输入分组名称')
    return
  }
  
  try {
    await groupsStore.createGroup({
      group_name: createForm.group_name,
      frps_server_id: props.serverId
    })
    alert('创建分组成功')
    showCreateDialog.value = false
    createForm.group_name = ''
  } catch (error) {
    alert('创建分组失败: ' + error.message)
  }
}

const editGroup = (group) => {
  currentGroup.value = group
  renameForm.new_name = group.group_name
  showRenameDialog.value = true
}

const handleRenameGroup = async () => {
  if (!renameForm.new_name || !currentGroup.value) {
    alert('请输入新分组名称')
    return
  }
  
  try {
    await groupsStore.updateGroup(
      currentGroup.value.group_name,
      renameForm.new_name,
      props.serverId
    )
    alert('重命名成功')
    showRenameDialog.value = false
  } catch (error) {
    alert('重命名失败: ' + error.message)
  }
}

const deleteGroup = async (group) => {
  const reassignGroup = prompt(
    `确定要删除分组 "${group.group_name}" 吗？该分组下有 ${group.total_count} 个代理。\n请输入目标分组名称（留空则移动到"其他"分组）：`
  )
  
  if (reassignGroup === null) {
    return
  }
  
  try {
    await groupsStore.deleteGroup(group.group_name, reassignGroup || '', props.serverId)
    alert('删除成功')
  } catch (error) {
    alert('删除失败: ' + error.message)
  }
}

const handleAutoAnalyze = async () => {
  try {
    await groupsStore.autoAnalyzeGroups(props.serverId)
    alert('自动分析分组成功')
    await groupsStore.loadGroups(props.serverId)
  } catch (error) {
    alert('自动分析失败: ' + error.message)
  }
}

const viewGroupProxies = (groupName) => {
  emit('view-group', groupName)
}

const generateGroupConfig = (groupName) => {
  emit('generate-config', groupName)
}

const closeCreateDialog = () => {
  showCreateDialog.value = false
  createForm.group_name = ''
}

const closeRenameDialog = () => {
  showRenameDialog.value = false
  renameForm.new_name = ''
}

// 使用统一的模态框功能
useModal(showCreateDialog, closeCreateDialog)
useModal(showRenameDialog, closeRenameDialog)
</script>

