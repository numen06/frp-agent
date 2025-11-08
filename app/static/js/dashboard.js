// 仪表板脚本

let servers = [];
let proxies = [];
let allProxies = []; // 保存所有代理用于过滤
let currentServerId = null;
let currentFilters = {
    group: '',
    status: ''
};
let selectedProxyIds = new Set(); // 选中的代理ID集合

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    // 显示用户名
    const username = localStorage.getItem('username') || '管理员';
    const usernameDisplay = document.getElementById('usernameDisplay');
    if (usernameDisplay) {
        usernameDisplay.textContent = username;
    }
    
    loadDashboard();
});

// 处理退出登录
function handleLogout() {
    if (confirm('确定要退出登录吗？')) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('username');
        localStorage.removeItem('currentServerId');
        window.location.href = '/login';
    }
}

// 加载仪表板数据
async function loadDashboard() {
    await loadServers();
    
    // 如果有保存的服务器选择，使用它；否则使用第一个服务器
    const savedServerId = localStorage.getItem('currentServerId');
    if (savedServerId && servers.find(s => s.id == savedServerId)) {
        currentServerId = parseInt(savedServerId);
    } else if (servers.length > 0) {
        currentServerId = parseInt(servers[0].id);
    }
    
    if (currentServerId) {
        document.getElementById('currentServerSelect').value = currentServerId;
        await loadProxiesForCurrentServer();
    }
    
    updateStats();
}

// 加载服务器列表
async function loadServers() {
    try {
        servers = await apiRequest('/api/servers');
        renderServersTable();
        updateServerSelects();
        updateCurrentServerInfo();
    } catch (error) {
        showNotification('加载服务器失败: ' + error.message, 'error');
    }
}

// 更新服务器选择器
function updateCurrentServerSelector() {
    const selector = document.getElementById('currentServerSelect');
    const currentValue = selector.value;
    
    selector.innerHTML = '<option value="">请选择服务器...</option>' +
        servers.map(s => `<option value="${s.id}" ${s.id == currentServerId ? 'selected' : ''}>${s.name}</option>`).join('');
    
    if (currentServerId) {
        selector.value = currentServerId;
    }
}

// 更新当前服务器信息显示
function updateCurrentServerInfo() {
    const container = document.getElementById('currentServerInfo');
    
    if (!currentServerId) {
        container.innerHTML = '<p style="color: #6b7280; padding: 1rem;">请选择一个服务器开始管理</p>';
        return;
    }
    
    const server = servers.find(s => s.id == currentServerId);
    if (!server) {
        container.innerHTML = '<p style="color: #ef4444; padding: 1rem;">服务器不存在</p>';
        return;
    }
    
    const statusInfo = getServerStatusInfo(server);
    
    container.innerHTML = `
        <div style="background: #f9fafb; padding: 1rem; border-radius: 0.375rem; margin-top: 1rem;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div>
                    <div style="color: #6b7280; font-size: 0.875rem;">服务器地址</div>
                    <div style="font-weight: 500;">${server.server_addr}:${server.server_port}</div>
                </div>
                <div>
                    <div style="color: #6b7280; font-size: 0.875rem;">API 地址</div>
                    <div style="font-weight: 500; font-size: 0.875rem;">${server.api_base_url}</div>
                </div>
                <div>
                    <div style="color: #6b7280; font-size: 0.875rem;">认证用户名</div>
                    <div style="font-weight: 500;">${server.auth_username}</div>
                </div>
                <div>
                    <div style="color: #6b7280; font-size: 0.875rem;">连接状态</div>
                    <div>
                        <span class="badge ${statusInfo.badgeClass}" title="${statusInfo.message}">
                            ${statusInfo.text}
                        </span>
                        ${server.last_test_time ? `<div style="color: #6b7280; font-size: 0.75rem; margin-top: 0.25rem;">测试时间: ${formatDateTime(server.last_test_time)}</div>` : ''}
                    </div>
                </div>
            </div>
            ${statusInfo.message && statusInfo.text !== '在线' ? `
                <div style="margin-top: 0.75rem; padding: 0.5rem; background: #fee; border-left: 3px solid #ef4444; color: #991b1b; font-size: 0.875rem;">
                    ${statusInfo.message}
                </div>
            ` : ''}
        </div>
    `;
}

// 切换服务器
async function switchServer() {
    const selector = document.getElementById('currentServerSelect');
    const newServerId = selector.value;
    
    if (!newServerId) {
        currentServerId = null;
        localStorage.removeItem('currentServerId');
        proxies = [];
        renderProxiesTable();
        updateStats();
        updateCurrentServerInfo();
        return;
    }
    
    currentServerId = parseInt(newServerId);
    localStorage.setItem('currentServerId', currentServerId);
    
    await loadProxiesForCurrentServer();
    updateCurrentServerInfo();
}

// 加载当前服务器的代理
async function loadProxiesForCurrentServer() {
    if (!currentServerId) {
        proxies = [];
        allProxies = [];
        renderProxiesTable();
        updateStats();
        updateGroupFilter();
        return;
    }
    
    try {
        // 新的API返回格式: {proxies: [...], analysis: {...}}
        const response = await apiRequest(`/api/proxies?frps_server_id=${currentServerId}&sync_from_frps=true`);
        
        // 处理新的响应格式
        if (response.proxies) {
            allProxies = response.proxies;
        } else if (Array.isArray(response)) {
            // 兼容旧格式
            allProxies = response.filter(p => p.frps_server_id == currentServerId);
        } else {
            allProxies = [];
        }
        
        // 显示对比分析信息（如果有）
        if (response.analysis && !response.analysis.error) {
            showAnalysisInfo(response.analysis);
        } else if (response.analysis && response.analysis.error) {
            showAnalysisError(response.analysis.error);
        }
        
        // 更新分组过滤器
        updateGroupFilter();
        
        // 应用当前过滤器
        applyFilters();
        
    } catch (error) {
        showNotification('加载代理失败: ' + error.message, 'error');
    }
}

// 显示对比分析信息
function showAnalysisInfo(analysis) {
    const container = document.getElementById('analysisInfo');
    if (!analysis || !container) return;
    
    const badges = [];
    
    if (analysis.total_in_db > 0) {
        badges.push(`<span class="badge badge-secondary">📊 本地: ${analysis.total_in_db}</span>`);
    }
    
    if (analysis.total_in_frps > 0) {
        badges.push(`<span class="badge badge-secondary">☁️ frps: ${analysis.total_in_frps}</span>`);
    }
    
    if (analysis.online_proxies && analysis.online_proxies.length > 0) {
        badges.push(`<span class="badge badge-online">✓ 在线: ${analysis.online_proxies.length}</span>`);
    }
    
    if (analysis.status_changed && analysis.status_changed.length > 0) {
        badges.push(`<span class="badge" style="background: #f59e0b;">🔄 状态变更: ${analysis.status_changed.length}</span>`);
    }
    
    if (analysis.missing_in_frps && analysis.missing_in_frps.length > 0) {
        badges.push(`<span class="badge" style="background: #ef4444;">⚠️ frps缺失: ${analysis.missing_in_frps.length}</span>`);
    }
    
    if (analysis.only_in_frps && analysis.only_in_frps.length > 0) {
        badges.push(`<span class="badge" style="background: #8b5cf6;">✨ 新发现: ${analysis.only_in_frps.length}</span>`);
    }
    
    if (badges.length > 0) {
        container.innerHTML = `
            <div style="padding: 0.75rem; background: #f9fafb; border-radius: 0.375rem; border-left: 3px solid #3b82f6;">
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
                    <strong style="color: #374151;">对比分析:</strong>
                    ${badges.join(' ')}
                    <small style="color: #6b7280; margin-left: auto;">💡 本地数据库是主数据源</small>
                </div>
            </div>
        `;
        console.log('对比分析详情:', analysis);
    } else {
        container.innerHTML = '';
    }
}

// 显示分析错误
function showAnalysisError(error) {
    const container = document.getElementById('analysisInfo');
    if (!container) return;
    
    container.innerHTML = `
        <div style="padding: 0.75rem; background: #fef2f2; border-radius: 0.375rem; border-left: 3px solid #ef4444;">
            <div style="color: #991b1b;">
                <strong>⚠️ 对比分析失败:</strong> ${error}
            </div>
        </div>
    `;
}

// 更新分组过滤器
function updateGroupFilter() {
    const groupFilter = document.getElementById('groupFilter');
    if (!groupFilter) return;
    
    // 获取所有唯一的分组
    const groups = new Set();
    allProxies.forEach(proxy => {
        if (proxy.group_name) {
            groups.add(proxy.group_name);
        }
    });
    
    const sortedGroups = Array.from(groups).sort();
    
    // 保存当前选择
    const currentValue = groupFilter.value;
    
    // 更新选项
    groupFilter.innerHTML = '<option value="">全部分组</option>' +
        sortedGroups.map(group => `<option value="${group}">${group}</option>`).join('');
    
    // 恢复选择
    if (currentValue && sortedGroups.includes(currentValue)) {
        groupFilter.value = currentValue;
    }
}

// 应用过滤器
function applyFilters() {
    const groupFilter = document.getElementById('groupFilter');
    const statusFilter = document.getElementById('statusFilter');
    
    currentFilters.group = groupFilter ? groupFilter.value : '';
    currentFilters.status = statusFilter ? statusFilter.value : '';
    
    // 过滤代理列表
    proxies = allProxies.filter(proxy => {
        // 分组过滤
        if (currentFilters.group && proxy.group_name !== currentFilters.group) {
            return false;
        }
        
        // 状态过滤
        if (currentFilters.status && proxy.status !== currentFilters.status) {
            return false;
        }
        
        return true;
    });
    
    renderProxiesTable();
    updateStats();
}

// 刷新代理列表
async function refreshProxies() {
    await loadProxiesForCurrentServer();
    showNotification('代理列表已刷新', 'success');
}

// 切换主标签页
function switchMainTab(tab) {
    // 更新标签按钮状态
    document.querySelectorAll('.tabs .tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // 切换内容
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    if (tab === 'proxies') {
        document.getElementById('proxiesTab').classList.add('active');
    } else if (tab === 'groups') {
        document.getElementById('groupsTab').classList.add('active');
        // 加载分组管理表格
        loadGroupsManagement();
    }
}

// 测试当前服务器
async function testCurrentServer() {
    if (!currentServerId) {
        showNotification('请先选择一个服务器', 'error');
        return;
    }
    
    await testServer(currentServerId);
}

// 渲染服务器表格
function renderServersTable() {
    const container = document.getElementById('serversTable');
    
    if (servers.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">暂无服务器配置</p>';
        return;
    }
    
    const html = `
        <table>
            <thead>
                <tr>
                    <th>名称</th>
                    <th>地址</th>
                    <th>端口</th>
                    <th>连接状态</th>
                    <th>最后测试</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                ${servers.map(server => {
                    const statusInfo = getServerStatusInfo(server);
                    return `
                        <tr>
                            <td>${server.name}</td>
                            <td>${server.server_addr}</td>
                            <td>${server.server_port}</td>
                            <td>
                                <span class="badge ${statusInfo.badgeClass}" title="${statusInfo.message}">
                                    ${statusInfo.text}
                                </span>
                            </td>
                            <td>
                                ${server.last_test_time ? formatDateTime(server.last_test_time) : '未测试'}
                            </td>
                            <td>
                                <button class="btn btn-primary btn-small" onclick="openEditServerModal(${server.id})">编辑</button>
                                <button class="btn btn-secondary btn-small" onclick="testServer(${server.id})">测试</button>
                                <button class="btn btn-danger btn-small" onclick="deleteServer(${server.id})">删除</button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

// 获取服务器状态信息
function getServerStatusInfo(server) {
    if (!server.last_test_status || server.last_test_status === 'unknown') {
        return {
            text: '未知',
            badgeClass: 'badge-offline',
            message: '未进行连接测试'
        };
    }
    
    if (server.last_test_status === 'online') {
        return {
            text: '在线',
            badgeClass: 'badge-active',
            message: server.last_test_message || '连接成功'
        };
    }
    
    return {
        text: '离线',
        badgeClass: 'badge-offline',
        message: server.last_test_message || '连接失败'
    };
}

// 加载代理列表（保留用于其他地方调用）
async function loadProxies() {
    await loadProxiesForCurrentServer();
}

// 渲染代理表格
function renderProxiesTable() {
    const container = document.getElementById('proxiesTable');
    
    if (proxies.length === 0) {
        const filterInfo = [];
        if (currentFilters.group) filterInfo.push(`分组: ${currentFilters.group}`);
        if (currentFilters.status) filterInfo.push(`状态: ${currentFilters.status}`);
        
        const message = filterInfo.length > 0 
            ? `未找到符合条件的代理 (${filterInfo.join(', ')})`
            : '暂无代理配置';
            
        container.innerHTML = `<p style="text-align: center; color: #6b7280; padding: 2rem;">${message}</p>`;
        return;
    }
    
    const html = `
        <div style="margin-bottom: 0.5rem; color: #6b7280; font-size: 0.875rem; display: flex; justify-content: space-between; align-items: center;">
            <span>显示 ${proxies.length} 个代理 ${allProxies.length > proxies.length ? `/ 共 ${allProxies.length} 个` : ''}</span>
            <label style="cursor: pointer;">
                <input type="checkbox" id="selectAllCheckbox" onchange="toggleSelectAll(this.checked)" style="margin-right: 0.5rem;">
                全选
            </label>
        </div>
        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">选择</th>
                    <th>分组</th>
                    <th>名称</th>
                    <th>类型</th>
                    <th>远程端口</th>
                    <th>本地地址</th>
                    <th>状态</th>
                    <th>更新时间</th>
                </tr>
            </thead>
            <tbody>
                ${proxies.map(proxy => `
                    <tr>
                        <td style="text-align: center;">
                            <input type="checkbox" 
                                   class="proxy-checkbox" 
                                   value="${proxy.id}" 
                                   onchange="handleProxySelection()"
                                   ${selectedProxyIds.has(proxy.id) ? 'checked' : ''}>
                        </td>
                        <td>
                            ${proxy.group_name 
                                ? `<span class="badge" style="background: ${getGroupColor(proxy.group_name)}; color: white; font-weight: 600;">${proxy.group_name}</span>` 
                                : '<span style="color: #9ca3af;">-</span>'}
                        </td>
                        <td><strong>${proxy.name}</strong></td>
                        <td>${proxy.proxy_type.toUpperCase()}</td>
                        <td>${formatPort(proxy.remote_port)}</td>
                        <td style="font-family: monospace; font-size: 0.875rem;">${proxy.local_ip}:${proxy.local_port}</td>
                        <td>${statusBadge(proxy.status)}</td>
                        <td>${formatDateTime(proxy.updated_at)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
    updateSelectAllCheckbox();
}

// 处理代理选择
function handleProxySelection() {
    const checkboxes = document.querySelectorAll('.proxy-checkbox');
    selectedProxyIds.clear();
    
    checkboxes.forEach(cb => {
        if (cb.checked) {
            selectedProxyIds.add(parseInt(cb.value));
        }
    });
    
    updateBulkActionBar();
    updateSelectAllCheckbox();
}

// 全选/取消全选
function toggleSelectAll(checked) {
    const checkboxes = document.querySelectorAll('.proxy-checkbox');
    selectedProxyIds.clear();
    
    checkboxes.forEach(cb => {
        cb.checked = checked;
        if (checked) {
            selectedProxyIds.add(parseInt(cb.value));
        }
    });
    
    updateBulkActionBar();
}

// 更新全选复选框状态
function updateSelectAllCheckbox() {
    const selectAllCb = document.getElementById('selectAllCheckbox');
    if (!selectAllCb) return;
    
    const checkboxes = document.querySelectorAll('.proxy-checkbox');
    const checkedCount = document.querySelectorAll('.proxy-checkbox:checked').length;
    
    selectAllCb.checked = checkboxes.length > 0 && checkedCount === checkboxes.length;
    selectAllCb.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
}

// 更新批量操作工具栏
function updateBulkActionBar() {
    const bar = document.getElementById('bulkActionBar');
    const count = document.getElementById('selectedCount');
    const groupSelect = document.getElementById('bulkGroupSelect');
    
    if (selectedProxyIds.size > 0) {
        bar.style.display = 'block';
        count.textContent = `已选择 ${selectedProxyIds.size} 个代理`;
        
        // 更新分组选择器
        updateBulkGroupSelect();
    } else {
        bar.style.display = 'none';
    }
}

// 更新批量操作的分组选择器
function updateBulkGroupSelect() {
    const select = document.getElementById('bulkGroupSelect');
    if (!select) return;
    
    const groups = new Set();
    allProxies.forEach(proxy => {
        if (proxy.group_name) {
            groups.add(proxy.group_name);
        }
    });
    
    select.innerHTML = '<option value="">选择目标分组...</option>' +
        '<option value="_new_">+ 创建新分组</option>' +
        Array.from(groups).sort().map(g => `<option value="${g}">${g}</option>`).join('');
}

// 批量分配到分组
async function bulkAssignGroup() {
    const select = document.getElementById('bulkGroupSelect');
    let groupName = select.value;
    
    if (!groupName) {
        showNotification('请选择目标分组', 'error');
        return;
    }
    
    // 如果选择创建新分组
    if (groupName === '_new_') {
        groupName = prompt('请输入新分组名称：');
        if (!groupName) return;
    }
    
    if (!confirm(`确定要将 ${selectedProxyIds.size} 个代理分配到分组 "${groupName}" 吗？`)) {
        return;
    }
    
    try {
        const result = await apiRequest('/api/groups/batch-update', {
            method: 'PUT',
            body: JSON.stringify({
                proxy_ids: Array.from(selectedProxyIds),
                group_name: groupName
            })
        });
        
        if (result.success) {
            showNotification(result.message, 'success');
            clearSelection();
            await refreshProxies();
        }
    } catch (error) {
        showNotification('分配失败: ' + error.message, 'error');
    }
}

// 清除选择
function clearSelection() {
    selectedProxyIds.clear();
    document.querySelectorAll('.proxy-checkbox').forEach(cb => cb.checked = false);
    updateBulkActionBar();
    updateSelectAllCheckbox();
}

// 为选中的代理生成配置
function generateConfigForSelected() {
    if (selectedProxyIds.size === 0) {
        showNotification('请先选择代理', 'error');
        return;
    }
    
    // 获取选中的代理信息
    const selectedProxies = allProxies.filter(p => selectedProxyIds.has(p.id));
    
    // 显示选中的代理列表（带分组颜色）
    const listHtml = selectedProxies.map(p => 
        `<span class="badge" style="margin: 0.25rem; background: ${getGroupColor(p.group_name)}; color: white; font-weight: 600;">
            ${p.group_name ? `[${p.group_name}] ` : ''}${p.name}
        </span>`
    ).join('');
    document.getElementById('selectedProxiesList').innerHTML = listHtml;
    
    openModal('configModal');
}

// 生成配置文件
async function generateConfigFromSelected() {
    const proxyIds = Array.from(selectedProxyIds);
    const format = document.getElementById('configFormat').value || 'ini';
    
    try {
        // 配置文件是纯文本格式，不能用 apiRequest（会尝试解析JSON）
        const response = await fetch('/api/frpc/config/by-proxies', {
            method: 'POST',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                proxy_ids: proxyIds,
                format: format
            })
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || 'Request failed');
        }
        
        const config = await response.text();
        
        document.getElementById('configOutput').innerHTML = `
            <pre style="background: #f3f4f6; padding: 1rem; border-radius: 0.375rem; overflow-x: auto; border: 1px solid #d1d5db;">${config}</pre>
        `;
    } catch (error) {
        showNotification('生成配置失败: ' + error.message, 'error');
    }
}

// 生成安装脚本
async function generateInstallScript() {
    const proxyIds = Array.from(selectedProxyIds);
    const selectedProxies = allProxies.filter(p => proxyIds.includes(p.id));
    
    // 检查是否所有代理都在同一分组
    const groups = new Set(selectedProxies.map(p => p.group_name));
    
    if (groups.size !== 1) {
        showNotification('请选择同一分组的代理', 'error');
        return;
    }
    
    const groupName = Array.from(groups)[0];
    
    try {
        // 脚本是纯文本格式，不能用 apiRequest
        const response = await fetch(
            `/api/frpc/install-script/by-group/${groupName}?frps_server_id=${currentServerId}`,
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
        
        const script = await response.text();
        
        document.getElementById('configOutput').innerHTML = `
            <pre style="background: #2d3748; color: #e2e8f0; padding: 1rem; border-radius: 0.375rem; overflow-x: auto; border: 1px solid #475569;">${script}</pre>
        `;
    } catch (error) {
        showNotification('生成脚本失败: ' + error.message, 'error');
    }
}

// 下载配置文件
function downloadConfigFile() {
    const configOutput = document.querySelector('#configOutput pre');
    if (!configOutput) {
        showNotification('请先生成配置', 'error');
        return;
    }
    
    const format = document.getElementById('configFormat').value || 'ini';
    const extension = format === 'toml' ? 'toml' : 'ini';
    
    const content = configOutput.textContent;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `frpc.${extension}`;
    a.click();
    URL.revokeObjectURL(url);
    showNotification('配置文件已下载', 'success');
}

// 根据分组名称生成颜色
function getGroupColor(groupName) {
    if (!groupName || groupName === '其他') {
        return '#9ca3af'; // 灰色
    }
    
    // 预定义的颜色方案 - 鲜艳且易区分
    const colors = [
        '#3b82f6', // 蓝色
        '#10b981', // 绿色
        '#f59e0b', // 橙色
        '#8b5cf6', // 紫色
        '#ef4444', // 红色
        '#06b6d4', // 青色
        '#ec4899', // 粉色
        '#84cc16', // 亮绿
        '#f97316', // 深橙
        '#6366f1', // 靛蓝
        '#14b8a6', // 蓝绿
        '#a855f7', // 亮紫
        '#f43f5e', // 玫瑰红
        '#22c55e', // 青草绿
        '#0ea5e9', // 天蓝
        '#d946ef', // 品红
        '#facc15', // 黄色
        '#fb923c'  // 珊瑚橙
    ];
    
    // 使用字符串哈希选择颜色
    let hash = 0;
    for (let i = 0; i < groupName.length; i++) {
        hash = groupName.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const index = Math.abs(hash) % colors.length;
    return colors[index];
}

// 更新统计数据
function updateStats() {
    const onlineCount = proxies.filter(p => p.status === 'online').length;
    const offlineCount = proxies.filter(p => p.status === 'offline').length;
    const uniquePorts = new Set(proxies.filter(p => p.remote_port).map(p => p.remote_port));
    
    // 显示过滤后的统计，如果有过滤则显示总数
    const isFiltered = currentFilters.group || currentFilters.status;
    const totalText = isFiltered ? ` / ${allProxies.length}` : '';
    
    document.getElementById('proxyCount').textContent = proxies.length + totalText;
    document.getElementById('onlineCount').textContent = onlineCount;
    document.getElementById('offlineCount').textContent = offlineCount;
    document.getElementById('portCount').textContent = uniquePorts.size;
}

// 更新服务器选择框
function updateServerSelects() {
    // 更新当前服务器选择器
    updateCurrentServerSelector();
    
    // 更新添加代理的服务器选择（只显示当前服务器）
    if (currentServerId) {
        const currentServer = servers.find(s => s.id == currentServerId);
        if (currentServer) {
            const serverSelect = document.getElementById('serverSelect');
            if (serverSelect) {
                serverSelect.innerHTML = `<option value="${currentServer.id}" selected>${currentServer.name}</option>`;
                serverSelect.disabled = true; // 禁用选择，因为只能添加到当前服务器
            }
        }
    }
    
    // 更新配置生成的服务器选择（只显示当前服务器）
    if (currentServerId) {
        const currentServer = servers.find(s => s.id == currentServerId);
        if (currentServer) {
            const configSelect = document.getElementById('configServerSelect');
            if (configSelect) {
                configSelect.innerHTML = `<option value="${currentServer.id}" selected>${currentServer.name}</option>`;
            }
        }
    }
}

// 提交服务器表单
async function submitServer(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);
    data.server_port = parseInt(data.server_port);
    
    try {
        const newServer = await apiRequest('/api/servers', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showNotification('服务器添加成功');
        closeModal('addServerModal');
        event.target.reset();
        await loadServers();
        
        // 如果是第一个服务器，自动选中它
        if (servers.length === 1) {
            currentServerId = parseInt(newServer.id);
            localStorage.setItem('currentServerId', currentServerId);
            document.getElementById('currentServerSelect').value = currentServerId;
            await loadProxiesForCurrentServer();
            updateCurrentServerInfo();
        }
    } catch (error) {
        showNotification('添加失败: ' + error.message, 'error');
    }
}

// 提交代理表单
async function submitProxy(event) {
    event.preventDefault();
    
    if (!currentServerId) {
        showNotification('请先选择一个服务器', 'error');
        return;
    }
    
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);
    data.frps_server_id = currentServerId; // 强制使用当前服务器
    data.local_port = parseInt(data.local_port);
    
    if (data.remote_port) {
        data.remote_port = parseInt(data.remote_port);
    } else {
        delete data.remote_port;
    }
    
    try {
        await apiRequest('/api/proxies', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showNotification('代理添加成功');
        closeModal('addProxyModal');
        event.target.reset();
        await loadProxies();
        updateStats();
    } catch (error) {
        showNotification('添加失败: ' + error.message, 'error');
    }
}

// 删除服务器
async function deleteServer(serverId) {
    if (!confirm('确定要删除这个服务器吗？相关的代理和端口分配也会被删除。')) {
        return;
    }
    
    try {
        await apiRequest(`/api/servers/${serverId}`, {
            method: 'DELETE'
        });
        
        showNotification('服务器已删除');
        await loadDashboard();
    } catch (error) {
        showNotification('删除失败: ' + error.message, 'error');
    }
}

// 删除代理
async function deleteProxy(proxyId) {
    if (!confirm('确定要删除这个代理吗？')) {
        return;
    }
    
    try {
        await apiRequest(`/api/proxies/${proxyId}`, {
            method: 'DELETE'
        });
        
        showNotification('代理已删除');
        await loadProxies();
        updateStats();
    } catch (error) {
        showNotification('删除失败: ' + error.message, 'error');
    }
}

// 同步所有服务器
async function syncAll() {
    if (!currentServerId) {
        showNotification('请先选择一个服务器', 'error');
        return;
    }
    
    showNotification('正在同步...', 'success');
    
    try {
        const result = await apiRequest(`/api/sync?frps_server_id=${currentServerId}`, {
            method: 'POST'
        });
        
        showNotification(`同步完成: 更新${result.updated}个，新增${result.new}个，离线${result.offline}个`);
        await loadProxies();
        updateStats();
        
        if (result.conflicts && result.conflicts.length > 0) {
            showNotification(`检测到 ${result.conflicts.length} 个冲突`, 'error');
        }
    } catch (error) {
        showNotification('同步失败: ' + error.message, 'error');
    }
}

// 生成配置文件
async function generateConfig() {
    if (!currentServerId) {
        showNotification('请先选择服务器', 'error');
        return;
    }
    
    if (proxies.length === 0) {
        showNotification('当前服务器没有代理配置', 'error');
        return;
    }
    
    const requestData = {
        frps_server_id: currentServerId,
        proxies: proxies.map(p => ({
            name: p.name,
            type: p.proxy_type,
            local_ip: p.local_ip,
            local_port: p.local_port,
            remote_port: p.remote_port
        }))
    };
    
    try {
        const result = await apiRequest('/api/config/generate', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        const output = document.getElementById('configOutput');
        output.innerHTML = `
            <div class="form-group">
                <label>frpc.toml 配置内容</label>
                <textarea readonly style="font-family: monospace; height: 300px;">${result.config_content}</textarea>
            </div>
            <button class="btn btn-primary" onclick="downloadConfig()">下载配置文件</button>
        `;
        
        showNotification('配置生成成功');
    } catch (error) {
        showNotification('生成失败: ' + error.message, 'error');
    }
}

// 下载配置文件
async function downloadConfig() {
    if (!currentServerId) {
        showNotification('请先选择服务器', 'error');
        return;
    }
    
    const requestData = {
        frps_server_id: currentServerId,
        proxies: proxies.map(p => ({
            name: p.name,
            type: p.proxy_type,
            local_ip: p.local_ip,
            local_port: p.local_port,
            remote_port: p.remote_port
        }))
    };
    
    try {
        const response = await fetch('/api/config/download', {
            method: 'POST',
            headers: {
                'Authorization': AUTH_HEADER,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'frpc.toml';
        a.click();
        
        showNotification('配置文件已下载');
    } catch (error) {
        showNotification('下载失败: ' + error.message, 'error');
    }
}

// 下载 Linux 脚本
async function downloadLinuxScript() {
    try {
        const response = await fetch('/api/config/script/linux', {
            headers: {
                'Authorization': AUTH_HEADER
            }
        });
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'frpc.sh';
        a.click();
        
        showNotification('Linux 脚本已下载');
    } catch (error) {
        showNotification('下载失败: ' + error.message, 'error');
    }
}

// 下载 Windows 脚本
async function downloadWindowsScript() {
    try {
        const response = await fetch('/api/config/script/windows', {
            headers: {
                'Authorization': AUTH_HEADER
            }
        });
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'frpc.ps1';
        a.click();
        
        showNotification('Windows 脚本已下载');
    } catch (error) {
        showNotification('下载失败: ' + error.message, 'error');
    }
}

// 生成 API 地址（根据服务器地址）
function generateApiUrl() {
    const serverAddr = document.getElementById('server_addr').value;
    const apiUrlInput = document.getElementById('api_base_url');
    
    if (serverAddr && !apiUrlInput.value) {
        // 自动生成 API 地址
        let apiUrl = serverAddr;
        
        // 如果没有协议，添加 http://
        if (!apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
            apiUrl = 'http://' + apiUrl;
        }
        
        // 添加 /api 后缀
        if (!apiUrl.endsWith('/api')) {
            apiUrl = apiUrl.replace(/\/$/, '') + '/api';
        }
        
        apiUrlInput.value = apiUrl;
    }
}

// 生成编辑表单的 API 地址
function generateEditApiUrl() {
    const serverAddr = document.getElementById('edit_server_addr').value;
    const apiUrlInput = document.getElementById('edit_api_base_url');
    
    if (serverAddr) {
        // 自动生成 API 地址
        let apiUrl = serverAddr;
        
        // 如果没有协议，添加 http://
        if (!apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
            apiUrl = 'http://' + apiUrl;
        }
        
        // 添加 /api 后缀
        if (!apiUrl.endsWith('/api')) {
            apiUrl = apiUrl.replace(/\/$/, '') + '/api';
        }
        
        apiUrlInput.value = apiUrl;
    }
}

// 打开编辑服务器 Modal
async function openEditServerModal(serverId) {
    try {
        const server = await apiRequest(`/api/servers/${serverId}`);
        
        document.getElementById('edit_server_id').value = server.id;
        document.getElementById('edit_name').value = server.name;
        document.getElementById('edit_server_addr').value = server.server_addr;
        document.getElementById('edit_server_port').value = server.server_port;
        document.getElementById('edit_api_base_url').value = server.api_base_url;
        document.getElementById('edit_auth_username').value = server.auth_username;
        document.getElementById('edit_auth_password').value = '';
        document.getElementById('edit_auth_token').value = server.auth_token || '';
        
        openModal('editServerModal');
    } catch (error) {
        showNotification('加载服务器信息失败: ' + error.message, 'error');
    }
}

// 提交编辑服务器表单
async function submitEditServer(event) {
    event.preventDefault();
    
    const serverId = document.getElementById('edit_server_id').value;
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);
    
    // 移除 id 字段
    delete data.id;
    
    // 转换数据类型
    data.server_port = parseInt(data.server_port);
    
    // 如果密码为空，不更新密码
    if (!data.auth_password) {
        delete data.auth_password;
    }
    
    // 如果 auth_token 为空，删除该字段（允许清空）
    if (!data.auth_token) {
        data.auth_token = null;
    }
    
    try {
        await apiRequest(`/api/servers/${serverId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        
        showNotification('服务器更新成功');
        closeModal('editServerModal');
        await loadServers();
        
        // 如果编辑的是当前服务器，刷新当前服务器信息
        if (serverId == currentServerId) {
            updateCurrentServerInfo();
        }
    } catch (error) {
        showNotification('更新失败: ' + error.message, 'error');
    }
}

// 测试服务器连接（从表格）
async function testServer(serverId) {
    showNotification('正在测试连接...', 'success');
    
    try {
        const result = await apiRequest(`/api/servers/${serverId}/test`, {
            method: 'POST'
        });
        
        // 重新加载服务器列表以更新状态
        await loadServers();
        
        // 如果测试的是当前服务器，刷新当前服务器信息
        if (serverId == currentServerId) {
            updateCurrentServerInfo();
        }
        
        if (result.success) {
            showNotification('✓ ' + result.message, 'success');
        } else {
            showNotification('✗ ' + result.message, 'error');
        }
    } catch (error) {
        showNotification('测试失败: ' + error.message, 'error');
    }
}

// 测试服务器连接（从添加表单）
async function testServerConnection() {
    const form = document.getElementById('serverForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // 验证必填字段
    if (!data.server_addr || !data.api_base_url || !data.auth_username || !data.auth_password) {
        showNotification('请先填写服务器地址、API地址、用户名和密码', 'error');
        return;
    }
    
    showNotification('正在测试连接...', 'success');
    
    try {
        // 创建临时测试请求
        const response = await fetch(data.api_base_url.replace(/\/$/, '') + '/proxy/tcp', {
            method: 'GET',
            headers: {
                'Authorization': 'Basic ' + btoa(data.auth_username + ':' + data.auth_password)
            },
            timeout: 10000
        });
        
        if (response.ok) {
            showNotification('✓ 连接成功', 'success');
        } else if (response.status === 401) {
            showNotification('✗ 认证失败，请检查用户名和密码', 'error');
        } else {
            showNotification('✗ 服务器返回错误: ' + response.status, 'error');
        }
    } catch (error) {
        showNotification('✗ 连接失败: ' + error.message, 'error');
    }
}

// 测试服务器连接（从编辑表单）
async function testEditServerConnection() {
    const form = document.getElementById('editServerForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // 验证必填字段
    if (!data.server_addr || !data.api_base_url || !data.auth_username) {
        showNotification('请先填写服务器地址、API地址和用户名', 'error');
        return;
    }
    
    showNotification('正在测试连接...', 'success');
    
    // 如果没有填写密码，使用原服务器的密码进行测试
    const serverId = document.getElementById('edit_server_id').value;
    
    try {
        const result = await apiRequest(`/api/servers/${serverId}/test`, {
            method: 'POST'
        });
        
        if (result.success) {
            showNotification('✓ ' + result.message, 'success');
        } else {
            showNotification('✗ ' + result.message, 'error');
        }
    } catch (error) {
        showNotification('测试失败: ' + error.message, 'error');
    }
}

