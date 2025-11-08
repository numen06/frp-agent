// ==================== 独立的分组管理功能 ====================

// 加载分组管理表格
async function loadGroupsManagement() {
    const container = document.getElementById('groupsManageTable');
    
    if (!currentServerId) {
        container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">请先选择服务器</p>';
        return;
    }
    
    try {
        const response = await apiRequest(`/api/groups?frps_server_id=${currentServerId}`);
        const groups = response.groups || [];
        
        if (groups.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">暂无分组</p>';
            return;
        }
        
        const html = `
            <table>
                <thead>
                    <tr>
                        <th>分组名称</th>
                        <th>代理数量</th>
                        <th>在线</th>
                        <th>离线</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${groups.map(group => `
                        <tr>
                            <td>
                                <strong style="color: #3b82f6;">${group.group_name}</strong>
                            </td>
                            <td>${group.total_count}</td>
                            <td><span class="badge badge-online">${group.online_count}</span></td>
                            <td><span class="badge badge-offline">${group.offline_count}</span></td>
                            <td>
                                <button class="btn btn-secondary btn-small" onclick="viewGroupProxies('${group.group_name}')">查看代理</button>
                                <button class="btn btn-secondary btn-small" onclick="openRenameGroupModal('${group.group_name}')">重命名</button>
                                <button class="btn btn-success btn-small" onclick="generateGroupConfig('${group.group_name}')">生成配置</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<p style="text-align: center; color: #ef4444; padding: 2rem;">加载失败: ${error.message}</p>`;
    }
}

// 查看分组的代理
function viewGroupProxies(groupName) {
    // 切换到代理列表标签页
    const proxiesTabBtn = document.querySelector('.tabs .tab-btn:first-child');
    proxiesTabBtn.click();
    
    // 设置过滤器并应用
    setTimeout(() => {
        document.getElementById('groupFilter').value = groupName;
        applyFilters();
        showNotification(`已切换到分组: ${groupName}`, 'success');
    }, 100);
}

// 打开创建分组Modal（实际上是通过选择代理来创建）
function openCreateGroupModal() {
    // 切换到代理列表标签页
    const proxiesTabBtn = document.querySelector('.tabs .tab-btn:first-child');
    proxiesTabBtn.click();
    
    setTimeout(() => {
        showNotification('💡 提示：在代理列表中勾选代理，然后选择"分配到分组"即可创建新分组', 'success');
    }, 100);
}

// 打开重命名分组Modal
function openRenameGroupModal(groupName) {
    document.getElementById('groupModalTitle').textContent = '重命名分组';
    document.getElementById('groupOldName').value = groupName;
    document.getElementById('groupNewName').value = groupName;
    openModal('groupModal');
}

// 提交分组表单（重命名）
async function submitGroupForm(event) {
    event.preventDefault();
    
    const oldName = document.getElementById('groupOldName').value;
    const newName = document.getElementById('groupNewName').value.trim();
    
    if (!newName) {
        showNotification('请输入分组名称', 'error');
        return;
    }
    
    if (oldName === newName) {
        showNotification('新分组名称与旧名称相同', 'error');
        return;
    }
    
    try {
        const result = await apiRequest('/api/groups/rename', {
            method: 'POST',
            body: JSON.stringify({
                old_name: oldName,
                new_name: newName,
                frps_server_id: currentServerId
            })
        });
        
        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('groupModal');
            await refreshProxies();
        }
    } catch (error) {
        showNotification('操作失败: ' + error.message, 'error');
    }
}

// 为分组生成配置
async function generateGroupConfig(groupName) {
    try {
        const config = await apiRequest(
            `/api/frpc/config/by-group/${groupName}?frps_server_id=${currentServerId}`
        );
        
        // 创建下载
        const blob = new Blob([config], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `frpc_${groupName}.ini`;
        a.click();
        URL.revokeObjectURL(url);
        
        showNotification(`已生成分组 "${groupName}" 的配置文件`, 'success');
    } catch (error) {
        showNotification('生成配置失败: ' + error.message, 'error');
    }
}

// 自动分析分组
async function autoAnalyzeGroups() {
    if (!currentServerId) {
        showNotification('请先选择服务器', 'error');
        return;
    }
    
    if (!confirm('将从所有代理名称中自动分析分组，并更新分组归属。是否继续？')) {
        return;
    }
    
    try {
        showNotification('正在分析分组...', 'success');
        
        const result = await apiRequest('/api/groups/auto-analyze', {
            method: 'POST',
            body: JSON.stringify({
                frps_server_id: currentServerId
            })
        });
        
        if (result.success) {
            const analysis = result.analysis;
            
            // 显示详细结果
            let message = `✓ 分析完成！\n\n`;
            message += `总代理数: ${analysis.total}\n`;
            message += `更新数量: ${analysis.updated}\n`;
            message += `未变化: ${analysis.unchanged}\n\n`;
            
            message += `发现的分组:\n`;
            Object.entries(analysis.groups_found).forEach(([group, count]) => {
                message += `  • ${group}: ${count} 个代理\n`;
            });
            
            if (analysis.new_groups && analysis.new_groups.length > 0) {
                message += `\n新识别的分组: ${analysis.new_groups.join(', ')}`;
            }
            
            alert(message);
            
            // 刷新数据
            await loadGroupsManagement();
            await refreshProxies();
            
            showNotification(result.message, 'success');
        }
    } catch (error) {
        showNotification('分析失败: ' + error.message, 'error');
    }
}
