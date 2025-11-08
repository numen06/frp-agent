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
                                <button class="btn btn-danger btn-small" onclick="openDeleteGroupModal('${group.group_name}', ${group.total_count})">删除</button>
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

// 打开创建分组Modal
function openCreateGroupModal() {
    // 重置表单
    document.getElementById('createGroupForm').reset();
    openModal('createGroupModal');
}

// 提交创建分组表单
async function submitCreateGroup(event) {
    event.preventDefault();
    
    if (!currentServerId) {
        showNotification('请先选择服务器', 'error');
        return;
    }
    
    const groupName = document.getElementById('new_group_name').value.trim();
    
    if (!groupName) {
        showNotification('请输入分组名称', 'error');
        return;
    }
    
    try {
        const result = await apiRequest('/api/groups/create', {
            method: 'POST',
            body: JSON.stringify({
                group_name: groupName,
                frps_server_id: currentServerId
            })
        });
        
        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('createGroupModal');
            
            // 刷新分组管理表格
            await loadGroupsManagement();
        }
    } catch (error) {
        showNotification('创建失败: ' + error.message, 'error');
    }
}

// 打开删除分组Modal
function openDeleteGroupModal(groupName, proxyCount) {
    document.getElementById('delete_group_name').value = groupName;
    document.getElementById('delete_group_name_display').textContent = groupName;
    document.getElementById('delete_group_proxy_count').textContent = proxyCount;
    
    // 填充重新分配的分组选项
    const reassignSelect = document.getElementById('delete_reassign_group');
    const groups = new Set();
    allProxies.forEach(proxy => {
        if (proxy.group_name && proxy.group_name !== groupName && proxy.group_name !== '其他') {
            groups.add(proxy.group_name);
        }
    });
    
    reassignSelect.innerHTML = '<option value="">移动到"其他"分组</option>' +
        Array.from(groups).sort().map(g => `<option value="${g}">${g}</option>`).join('');
    
    openModal('deleteGroupModal');
}

// 提交删除分组表单
async function submitDeleteGroup(event) {
    event.preventDefault();
    
    if (!currentServerId) {
        showNotification('请先选择服务器', 'error');
        return;
    }
    
    const groupName = document.getElementById('delete_group_name').value;
    const reassignGroup = document.getElementById('delete_reassign_group').value;
    
    try {
        let url = `/api/groups/${encodeURIComponent(groupName)}?frps_server_id=${currentServerId}`;
        if (reassignGroup) {
            url += `&reassign_group=${encodeURIComponent(reassignGroup)}`;
        }
        
        const result = await apiRequest(url, {
            method: 'DELETE'
        });
        
        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('deleteGroupModal');
            
            // 刷新分组管理表格和代理列表
            await loadGroupsManagement();
            await refreshProxies();
        }
    } catch (error) {
        showNotification('删除失败: ' + error.message, 'error');
    }
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
async function generateGroupConfig(groupName, format = 'ini') {
    // 如果没有指定格式，询问用户
    if (!format) {
        const userChoice = confirm('选择配置格式：\n\n点击"确定"使用 TOML 格式（推荐，新版本FRP）\n点击"取消"使用 INI 格式（兼容旧版本）');
        format = userChoice ? 'toml' : 'ini';
    }
    
    try {
        // 配置文件是纯文本，不能用 apiRequest
        const response = await fetch(
            `/api/frpc/config/by-group/${groupName}?frps_server_id=${currentServerId}&format=${format}`,
            {
                headers: {
                    'Authorization': getAuthHeader()
                }
            }
        );
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || 'Request failed');
        }
        
        const config = await response.text();
        
        // 根据格式设置文件扩展名
        const extension = format === 'toml' ? 'toml' : 'ini';
        
        // 创建下载
        const blob = new Blob([config], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `frpc_${groupName}.${extension}`;
        a.click();
        URL.revokeObjectURL(url);
        
        showNotification(`已生成分组 "${groupName}" 的 ${format.toUpperCase()} 配置文件`, 'success');
    } catch (error) {
        showNotification('生成配置失败: ' + error.message, 'error');
    }
}

// 自动分析分组
async function autoAnalyzeGroups() {
    console.log('=== 开始自动分析分组 ===');
    console.log('currentServerId:', currentServerId);
    console.log('typeof currentServerId:', typeof currentServerId);
    
    if (!currentServerId) {
        console.error('❌ currentServerId 为空或未定义');
        showNotification('请先选择服务器', 'error');
        return;
    }
    
    console.log('✓ currentServerId 存在:', currentServerId);
    
    if (!confirm('将从代理名称中自动分析分组。\n\n注意：仅对分组为"其他"或空的代理进行分析，不会覆盖已有的分组。\n\n是否继续？')) {
        return;
    }
    
    try {
        showNotification('正在分析分组...', 'success');
        
        // 确保 frps_server_id 是整数
        const serverIdInt = parseInt(currentServerId);
        if (isNaN(serverIdInt)) {
            throw new Error('无效的服务器ID: ' + currentServerId);
        }
        
        const requestBody = {
            frps_server_id: serverIdInt
        };
        
        console.log('请求体:', requestBody);
        console.log('请求JSON:', JSON.stringify(requestBody));
        
        const result = await apiRequest('/api/groups/auto-analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('API返回的原始结果:', result);
        console.log('result类型:', typeof result);
        console.log('result.success:', result?.success);
        
        if (result && result.success) {
            const analysis = result.analysis;
            
            // 显示详细结果
            let message = `✓ 分析完成！\n\n`;
            message += `总代理数: ${analysis.total}\n`;
            message += `更新数量: ${analysis.updated}\n`;
            message += `跳过数量: ${analysis.skipped} (已有分组)\n`;
            message += `未变化: ${analysis.unchanged}\n\n`;
            
            message += `发现的分组:\n`;
            Object.entries(analysis.groups_found).sort().forEach(([group, count]) => {
                message += `  • ${group}: ${count} 个代理\n`;
            });
            
            if (analysis.new_groups && analysis.new_groups.length > 0) {
                message += `\n新识别的分组: ${analysis.new_groups.join(', ')}`;
            }
            
            alert(message);
            
            // 刷新数据
            showNotification('正在刷新数据...', 'success');
            await loadGroupsManagement();
            await refreshProxies();
            
            showNotification(result.message, 'success');
        } else {
            console.error('分析结果异常:', result);
            showNotification('分析失败: 服务器返回结果异常', 'error');
        }
    } catch (error) {
        console.error('分析分组错误:', error);
        console.error('错误类型:', typeof error);
        console.error('错误对象:', error);
        
        let errorMsg = '未知错误';
        
        if (typeof error === 'string') {
            errorMsg = error;
        } else if (error && error.message) {
            errorMsg = error.message;
        } else if (error && error.detail) {
            errorMsg = error.detail;
        } else {
            try {
                errorMsg = JSON.stringify(error);
            } catch (e) {
                errorMsg = String(error);
            }
        }
        
        // 显示完整的错误消息
        alert('分析失败:\n\n' + errorMsg + '\n\n请查看控制台获取更多信息');
        showNotification('分析失败: ' + errorMsg, 'error');
    }
}

// 调试函数
async function debugAutoAnalyze() {
    console.log('=== 调试模式 ===');
    
    const info = {
        currentServerId: currentServerId,
        currentServerIdType: typeof currentServerId,
        hasAuthToken: !!localStorage.getItem('auth_token'),
        authTokenLength: localStorage.getItem('auth_token')?.length || 0
    };
    
    console.log('调试信息:', info);
    alert('调试信息（请查看控制台）:\n' + JSON.stringify(info, null, 2));
    
    if (!currentServerId) {
        alert('错误：currentServerId 为空！\n请确保已选择服务器。');
        return;
    }
    
    // 直接调用 fetch 测试
    try {
        console.log('直接测试 fetch...');
        
        const response = await fetch('/api/groups/auto-analyze', {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + localStorage.getItem('auth_token'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                frps_server_id: currentServerId
            })
        });
        
        console.log('响应状态:', response.status);
        console.log('响应headers:', Object.fromEntries(response.headers.entries()));
        
        const text = await response.text();
        console.log('响应文本:', text);
        
        try {
            const data = JSON.parse(text);
            console.log('响应JSON:', data);
            
            if (response.ok) {
                alert('✓ API调用成功！\n\n' + JSON.stringify(data, null, 2));
            } else {
                alert('✗ API返回错误\n状态码: ' + response.status + '\n\n' + JSON.stringify(data, null, 2));
            }
        } catch (e) {
            alert('✗ 响应不是JSON\n状态码: ' + response.status + '\n\n' + text);
        }
    } catch (error) {
        console.error('Fetch错误:', error);
        alert('✗ 请求失败:\n' + error.message);
    }
}
