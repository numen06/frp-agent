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

// 端口自动识别映射表（使用数组保持顺序，长关键字优先）
const PORT_MAPPINGS = [
    // 先检查长关键字和特殊关键字
    ['elasticsearch', 9200],
    ['postgresql', 5432],
    ['prometheus', 9090],
    ['minecraft', 25565],
    ['mariadb', 3306],
    ['mongodb', 27017],
    ['terraria', 7777],
    // HTTPS 必须在 HTTP 之前检查
    ['https', 443],
    // VNC 必须在 remote 之前检查
    ['vnc', 5900],
    // 远程桌面
    ['rdp', 3389],
    ['mstsc', 3389],
    ['remote', 3389],
    // SSH
    ['ssh', 22],
    ['sftp', 22],
    // HTTP/Web
    ['http', 80],
    ['web', 80],
    ['nginx', 80],
    ['apache', 80],
    // Docker
    ['docker', 9000],
    // MySQL
    ['mysql', 3306],
    // PostgreSQL
    ['postgres', 5432],
    ['pgsql', 5432],
    // Redis
    ['redis', 6379],
    // MongoDB
    ['mongo', 27017],
    // FTP
    ['ftp', 21],
    // SMTP
    ['smtps', 465],
    ['smtp', 25],
    // IMAP/POP3
    ['imaps', 993],
    ['imap', 143],
    ['pop3s', 995],
    ['pop3', 110],
    // DNS
    ['dns', 53],
    // NTP
    ['ntp', 123],
    // Game servers
    ['csgo', 27015],
    ['cs', 27015],
    ['mc', 25565],
    // Other common services
    ['es', 9200],
    ['kibana', 5601],
    ['grafana', 3000],
    ['jenkins', 8080],
    ['tomcat', 8080]
];

// 根据代理名称自动识别本地端口
function autoDetectLocalPort(proxyName) {
    if (!proxyName) return 0;
    
    const nameLower = proxyName.toLowerCase();
    
    // 先检查是否包含端口号（例如：dlyy_http_8080）
    const portPattern = /_(\d{2,5})$/;
    const match = nameLower.match(portPattern);
    if (match) {
        const port = parseInt(match[1]);
        if (port >= 1 && port <= 65535) {
            return port;
        }
    }
    
    // 先尝试完整单词匹配（使用下划线或开头/结尾作为边界）
    for (const [keyword, port] of PORT_MAPPINGS) {
        const pattern = new RegExp(`(^|_)${keyword}($|_)`);
        if (pattern.test(nameLower)) {
            return port;
        }
    }
    
    // 如果没有完整单词匹配，再尝试包含匹配（按顺序，长关键字优先）
    for (const [keyword, port] of PORT_MAPPINGS) {
        if (nameLower.includes(keyword)) {
            return port;
        }
    }
    
    return 0;
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    // 显示用户名
    const username = localStorage.getItem('username') || '管理员';
    const usernameDisplay = document.getElementById('usernameDisplay');
    if (usernameDisplay) {
        usernameDisplay.textContent = username;
    }
    
    // 为添加代理表单添加自动端口识别监听器
    setupAddProxyAutoDetection();
    
    loadDashboard();
});

// 为添加代理表单设置自动端口识别
function setupAddProxyAutoDetection() {
    const nameInput = document.getElementById('add_proxy_name');
    const portInput = document.getElementById('add_local_port');
    
    if (nameInput && portInput) {
        nameInput.addEventListener('input', function() {
            const currentPort = parseInt(portInput.value) || 0;
            // 如果当前端口为0，尝试自动识别
            if (currentPort === 0) {
                const detectedPort = autoDetectLocalPort(this.value);
                if (detectedPort > 0) {
                    portInput.value = detectedPort;
                    // 显示提示信息
                    const hint = portInput.nextElementSibling;
                    if (hint && hint.tagName === 'SMALL') {
                        const originalText = hint.innerHTML;
                        hint.innerHTML = `✅ 已自动识别端口: ${detectedPort}（可手动修改）`;
                        hint.style.color = '#10b981';
                        setTimeout(() => {
                            hint.style.color = '#6b7280';
                            hint.innerHTML = originalText;
                        }, 3000);
                    }
                }
            }
        });
        
        // 当端口输入框值变为0时，也尝试自动识别
        portInput.addEventListener('input', function() {
            const port = parseInt(this.value) || 0;
            if (port === 0 && nameInput.value) {
                const detectedPort = autoDetectLocalPort(nameInput.value);
                if (detectedPort > 0) {
                    this.value = detectedPort;
                    const hint = this.nextElementSibling;
                    if (hint && hint.tagName === 'SMALL') {
                        hint.innerHTML = `✅ 已自动识别端口: ${detectedPort}（可手动修改）`;
                        hint.style.color = '#10b981';
                        setTimeout(() => {
                            hint.style.color = '#6b7280';
                            hint.innerHTML = '本地服务的端口号（1-65535），输入 0 可根据名称自动识别（如 rdp→3389, ssh→22, http→80, docker→9000）';
                        }, 3000);
                    }
                }
            }
        });
    }
}

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
    } else if (tab === 'converter') {
        document.getElementById('converterTab').classList.add('active');
        // 更新 API URL 为真实地址
        updateApiUrlInHelp();
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
                    <th style="width: 120px;">操作</th>
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
                        <td>
                            <div style="display: flex; gap: 0.25rem; justify-content: center;">
                                <button class="btn-icon" onclick="showEditProxyModal(${proxy.id})" title="编辑">✏️</button>
                                <button class="btn-icon" onclick="deleteProxy(${proxy.id})" title="删除" style="color: #ef4444;">🗑️</button>
                            </div>
                        </td>
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
        
        // 注意：这里返回的是JSON格式，包含临时配置信息
        const result = await response.json();
        const config = result.config;
        
        // 检查是否所有代理都在同一分组
        const selectedProxies = allProxies.filter(p => proxyIds.includes(p.id));
        const groups = new Set(selectedProxies.map(p => p.group_name));
        
        let urlSection = '';
        if (result.temp_id) {
            // 这是临时配置（选择代理生成）
            const baseUrl = window.location.origin;
            const filename = result.format === 'toml' ? 'frpc.toml' : 'frpc.ini';
            const tempConfigUrl = `${baseUrl}/api/frpc/config/temp/${result.temp_id}`;
            
            const expiresDate = new Date(result.expires_at);
            const expiresStr = expiresDate.toLocaleString('zh-CN');
            
            urlSection = `
                <div style="margin-bottom: 1rem; padding: 1rem; background: #dbeafe; border-radius: 0.375rem; border: 1px solid #60a5fa;">
                    <h4 style="margin: 0 0 0.75rem 0; color: #1e40af;">🕐 临时配置访问地址（24小时有效）</h4>
                    
                    <div>
                        <div style="display: flex; gap: 0.5rem;">
                            <input type="text" readonly value="${tempConfigUrl}" 
                                id="configDirectUrl" 
                                style="flex: 1; padding: 0.5rem; border: 1px solid #60a5fa; border-radius: 0.375rem; background: white; font-family: monospace; font-size: 0.875rem;">
                            <button onclick="copyToClipboard('configDirectUrl', '配置URL已复制')" 
                                style="padding: 0.5rem 1rem; background: #3b82f6; color: white; border: none; border-radius: 0.375rem; cursor: pointer; font-weight: 600;">
                                📋 复制
                            </button>
                        </div>
                        <small style="color: #1e40af; display: block; margin-top: 0.5rem;">
                            💡 使用方法（无需认证）: <code style="background: white; padding: 0.125rem 0.375rem; border-radius: 0.25rem;">curl -f "${tempConfigUrl}" -o ${filename}</code>
                            <br>
                            <span style="color: #1e3a8a; font-size: 0.8em;">⏰ 过期时间: ${expiresStr}</span>
                            <br>
                            <span style="color: #dc2626; font-size: 0.8em; font-weight: 600;">⚠️ 此为临时配置，24小时后自动删除，仅用于测试</span>
                            <br>
                            <span style="color: #059669; font-size: 0.8em; font-weight: 600;">💡 推荐：日常使用请使用分组配置（长期有效）</span>
                        </small>
                    </div>
                </div>
            `;
        }
        
        document.getElementById('configOutput').innerHTML = `
            ${urlSection}
            <pre style="background: #f3f4f6; padding: 1rem; border-radius: 0.375rem; overflow-x: auto; border: 1px solid #d1d5db;">${config}</pre>
        `;
    } catch (error) {
        showNotification('生成配置失败: ' + error.message, 'error');
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
    
    let localPort = parseInt(data.local_port) || 0;
    
    // 如果本地端口为0，尝试自动识别
    if (localPort === 0) {
        const proxyName = data.name;
        localPort = autoDetectLocalPort(proxyName);
        if (localPort === 0) {
            showNotification('无法从代理名称自动识别本地端口，请手动指定', 'error');
            return;
        }
        showNotification(`已自动识别本地端口: ${localPort}`, 'info');
    }
    
    data.local_port = localPort;
    
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
        // 重置表单后，端口恢复为默认值0
        document.getElementById('add_local_port').value = 0;
        await loadProxiesForCurrentServer();
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

// 批量识别端口
async function batchDetectPorts() {
    if (!currentServerId) {
        showNotification('请先选择一个服务器', 'error');
        return;
    }
    
    if (!confirm('是否批量识别所有本地端口为 0 的代理？\n\n系统会根据代理名称自动识别端口（如 rdp→3389, ssh→22, http→80 等）')) {
        return;
    }
    
    showNotification('正在批量识别端口...', 'info');
    
    try {
        const result = await apiRequest(`/api/proxies/batch-detect-ports?frps_server_id=${currentServerId}`, {
            method: 'POST'
        });
        
        // 显示详细结果
        if (result.total === 0) {
            showNotification(result.message, 'info');
        } else {
            // 构建结果摘要
            let message = `✅ ${result.message}\n\n`;
            
            if (result.detected > 0) {
                message += `成功识别的代理：\n`;
                result.results
                    .filter(r => r.status === 'success')
                    .forEach(r => {
                        message += `  • ${r.name}: ${r.new_port}\n`;
                    });
            }
            
            if (result.failed > 0) {
                message += `\n无法识别的代理（需手动设置）：\n`;
                result.results
                    .filter(r => r.status === 'failed')
                    .forEach(r => {
                        message += `  • ${r.name}\n`;
                    });
            }
            
            // 使用自定义模态框显示详细结果
            showBatchDetectResultModal(result);
            
            // 刷新代理列表
            await loadProxiesForCurrentServer();
            updateStats();
        }
    } catch (error) {
        showNotification('批量识别失败: ' + error.message, 'error');
    }
}

// 显示批量识别结果模态框
function showBatchDetectResultModal(result) {
    const successList = result.results.filter(r => r.status === 'success');
    const failedList = result.results.filter(r => r.status === 'failed');
    
    let html = `
        <div style="padding: 1rem;">
            <div style="background: #f0f9ff; padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">
                <h3 style="margin: 0 0 0.5rem 0; color: #1e40af;">📊 批量识别结果</h3>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 1rem;">
                    <div>
                        <div style="color: #6b7280; font-size: 0.875rem;">总计</div>
                        <div style="font-size: 1.5rem; font-weight: 600; color: #374151;">${result.total}</div>
                    </div>
                    <div>
                        <div style="color: #6b7280; font-size: 0.875rem;">识别成功</div>
                        <div style="font-size: 1.5rem; font-weight: 600; color: #10b981;">${result.detected}</div>
                    </div>
                    <div>
                        <div style="color: #6b7280; font-size: 0.875rem;">识别失败</div>
                        <div style="font-size: 1.5rem; font-weight: 600; color: #ef4444;">${result.failed}</div>
                    </div>
                </div>
            </div>
    `;
    
    if (successList.length > 0) {
        html += `
            <div style="margin-bottom: 1rem;">
                <h4 style="color: #10b981; margin-bottom: 0.5rem;">✅ 识别成功（${successList.length}个）</h4>
                <div style="max-height: 200px; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 0.375rem;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead style="background: #f9fafb; position: sticky; top: 0;">
                            <tr>
                                <th style="padding: 0.5rem; text-align: left; border-bottom: 1px solid #e5e7eb;">代理名称</th>
                                <th style="padding: 0.5rem; text-align: left; border-bottom: 1px solid #e5e7eb;">分组</th>
                                <th style="padding: 0.5rem; text-align: center; border-bottom: 1px solid #e5e7eb;">识别端口</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${successList.map(r => `
                                <tr style="border-bottom: 1px solid #f3f4f6;">
                                    <td style="padding: 0.5rem;">${r.name}</td>
                                    <td style="padding: 0.5rem;">${r.group || '-'}</td>
                                    <td style="padding: 0.5rem; text-align: center; font-weight: 600; color: #10b981;">${r.new_port}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    if (failedList.length > 0) {
        html += `
            <div style="margin-bottom: 1rem;">
                <h4 style="color: #ef4444; margin-bottom: 0.5rem;">❌ 无法识别（${failedList.length}个）</h4>
                <div style="background: #fef2f2; padding: 1rem; border-radius: 0.375rem; border-left: 4px solid #ef4444;">
                    <p style="margin: 0 0 0.5rem 0; color: #991b1b; font-size: 0.875rem;">以下代理名称中未包含可识别的关键字，请手动编辑设置端口：</p>
                    <ul style="margin: 0; padding-left: 1.5rem; color: #7f1d1d;">
                        ${failedList.map(r => `<li>${r.name} (${r.group || '未分组'})</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
    }
    
    html += `
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb;">
                <button class="btn btn-primary" onclick="closeModal('batchDetectResultModal')" style="width: 100%;">关闭</button>
            </div>
        </div>
    `;
    
    // 创建或更新模态框
    let modal = document.getElementById('batchDetectResultModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'batchDetectResultModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <h2>🔍 批量识别端口结果</h2>
                    <span class="close-btn" onclick="closeModal('batchDetectResultModal')">&times;</span>
                </div>
                <div id="batchDetectResultContent"></div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    document.getElementById('batchDetectResultContent').innerHTML = html;
    openModal('batchDetectResultModal');
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

// 显示导入配置弹窗
function showImportConfigModal() {
    if (!currentServerId) {
        showNotification('请先选择一个服务器', 'error');
        return;
    }
    
    // 显示当前服务器
    const currentServer = servers.find(s => s.id == currentServerId);
    const serverDisplay = document.getElementById('importServerDisplay');
    if (currentServer) {
        serverDisplay.value = currentServer.name;
    }
    
    // 填充分组选择器
    const groupSelect = document.getElementById('importGroupSelect');
    const groups = new Set();
    allProxies.forEach(proxy => {
        if (proxy.group_name && proxy.group_name !== '其他') {
            groups.add(proxy.group_name);
        }
    });
    
    groupSelect.innerHTML = '<option value="">请选择分组...</option>' +
        '<option value="_new_">+ 创建新分组</option>' +
        Array.from(groups).sort().map(g => `<option value="${g}">${g}</option>`).join('');
    
    // 重置表单
    document.getElementById('importConfigForm').reset();
    document.getElementById('importProgress').style.display = 'none';
    document.getElementById('importResult').style.display = 'none';
    document.getElementById('importSubmitBtn').disabled = false;
    
    // 重新设置服务器显示（因为 reset 会清空）
    if (currentServer) {
        serverDisplay.value = currentServer.name;
    }
    
    openModal('importConfigModal');
}

// 导入配置文件
async function importConfig(event) {
    event.preventDefault();
    
    if (!currentServerId) {
        showNotification('请先选择一个服务器', 'error');
        return;
    }
    
    const form = event.target;
    const formData = new FormData(form);
    const fileInput = document.getElementById('configFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showNotification('请选择配置文件', 'error');
        return;
    }
    
    // 验证文件扩展名
    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.ini') && !fileName.endsWith('.toml')) {
        showNotification('仅支持 .ini 和 .toml 格式的配置文件', 'error');
        return;
    }
    
    // 获取分组名称
    let groupName = formData.get('group_name');
    if (!groupName) {
        showNotification('请选择分组', 'error');
        return;
    }
    
    // 如果选择创建新分组
    if (groupName === '_new_') {
        groupName = prompt('请输入新分组名称：');
        if (!groupName) return;
    }
    
    // 重新构建 FormData，添加服务器 ID
    const uploadFormData = new FormData();
    uploadFormData.append('file', file);
    uploadFormData.append('frps_server_id', currentServerId);
    uploadFormData.append('group_name', groupName);
    
    // 显示进度
    document.getElementById('importProgress').style.display = 'block';
    document.getElementById('importResult').style.display = 'none';
    document.getElementById('importSubmitBtn').disabled = true;
    
    try {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            throw new Error('未登录，请重新登录');
        }
        
        // 使用 fetch 直接上传文件
        const response = await fetch('/api/config/import', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: uploadFormData
        });
        
        const result = await response.json();
        
        // 隐藏进度
        document.getElementById('importProgress').style.display = 'none';
        
        if (response.ok && result.success) {
            // 显示成功结果
            let resultHtml = `
                <div style="background: #d1fae5; border: 1px solid #10b981; padding: 1rem; border-radius: 0.375rem;">
                    <p style="margin: 0 0 0.5rem 0; color: #065f46; font-weight: 600;">✓ ${result.message}</p>
                    <div style="color: #047857; font-size: 0.875rem;">
                        <p style="margin: 0.25rem 0;">• 新增: ${result.stats.created} 个</p>
                        <p style="margin: 0.25rem 0;">• 更新: ${result.stats.updated} 个</p>
                        <p style="margin: 0.25rem 0;">• 失败: ${result.stats.failed} 个</p>
                    </div>
            `;
            
            // 显示错误详情
            if (result.stats.errors && result.stats.errors.length > 0) {
                resultHtml += `
                    <div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #10b981;">
                        <p style="margin: 0.25rem 0; color: #dc2626; font-weight: 600;">错误详情:</p>
                        <ul style="margin: 0.25rem 0; padding-left: 1.5rem; color: #dc2626; font-size: 0.875rem;">
                `;
                result.stats.errors.forEach(err => {
                    resultHtml += `<li>${err.proxy_name}: ${err.error}</li>`;
                });
                resultHtml += `</ul></div>`;
            }
            
            resultHtml += `</div>`;
            
            document.getElementById('importResult').innerHTML = resultHtml;
            document.getElementById('importResult').style.display = 'block';
            
            showNotification(result.message, 'success');
            
            // 刷新代理列表
            setTimeout(() => {
                loadProxiesForCurrentServer();
                closeModal('importConfigModal');
            }, 2000);
            
        } else {
            // 显示错误
            const errorMsg = result.detail || result.message || '导入失败';
            document.getElementById('importResult').innerHTML = `
                <div style="background: #fee2e2; border: 1px solid #ef4444; padding: 1rem; border-radius: 0.375rem;">
                    <p style="margin: 0; color: #991b1b;">✗ ${errorMsg}</p>
                </div>
            `;
            document.getElementById('importResult').style.display = 'block';
            showNotification(errorMsg, 'error');
        }
    } catch (error) {
        document.getElementById('importProgress').style.display = 'none';
        document.getElementById('importResult').innerHTML = `
            <div style="background: #fee2e2; border: 1px solid #ef4444; padding: 1rem; border-radius: 0.375rem;">
                <p style="margin: 0; color: #991b1b;">✗ 导入失败: ${error.message}</p>
            </div>
        `;
        document.getElementById('importResult').style.display = 'block';
        showNotification('导入失败: ' + error.message, 'error');
    } finally {
        document.getElementById('importSubmitBtn').disabled = false;
    }
}

// 显示编辑代理弹窗
function showEditProxyModal(proxyId) {
    const proxy = allProxies.find(p => p.id === proxyId);
    if (!proxy) {
        showNotification('代理不存在', 'error');
        return;
    }
    
    // 填充表单
    document.getElementById('edit_proxy_id').value = proxy.id;
    document.getElementById('edit_proxy_name').value = proxy.name;
    document.getElementById('edit_group_name').value = proxy.group_name || '';
    document.getElementById('edit_proxy_type').value = proxy.proxy_type;
    document.getElementById('edit_local_ip').value = proxy.local_ip;
    document.getElementById('edit_local_port').value = proxy.local_port;
    document.getElementById('edit_remote_port').value = proxy.remote_port || '';
    
    // 添加代理名称变化监听器，自动识别端口
    const nameInput = document.getElementById('edit_proxy_name');
    const portInput = document.getElementById('edit_local_port');
    
    nameInput.addEventListener('input', function() {
        const currentPort = parseInt(portInput.value) || 0;
        // 如果当前端口为0或未设置，尝试自动识别
        if (!currentPort || currentPort === 0) {
            const detectedPort = autoDetectLocalPort(this.value);
            if (detectedPort > 0) {
                portInput.value = detectedPort;
                // 显示提示信息
                const hint = portInput.nextElementSibling;
                if (hint && hint.tagName === 'SMALL') {
                    hint.innerHTML = `已自动识别端口: ${detectedPort}（可手动修改）`;
                    hint.style.color = '#10b981';
                    setTimeout(() => {
                        hint.style.color = '#6b7280';
                        hint.innerHTML = '本地服务的端口号（1-65535），输入0自动识别';
                    }, 3000);
                }
            }
        }
    });
    
    openModal('editProxyModal');
}

// 提交编辑代理表单
async function submitEditProxy(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const proxyId = formData.get('proxy_id');
    let localPort = parseInt(formData.get('local_port')) || 0;
    
    // 如果本地端口为0，尝试自动识别
    if (localPort === 0) {
        const proxyName = formData.get('name');
        localPort = autoDetectLocalPort(proxyName);
        if (localPort === 0) {
            showNotification('无法从代理名称自动识别本地端口，请手动指定', 'error');
            return;
        }
    }
    
    const data = {
        name: formData.get('name'),
        group_name: formData.get('group_name') || null,
        proxy_type: formData.get('proxy_type'),
        local_ip: formData.get('local_ip'),
        local_port: localPort,
    };
    
    const remotePort = formData.get('remote_port');
    if (remotePort) {
        data.remote_port = parseInt(remotePort);
    }
    
    // 验证端口号
    if (data.local_port < 1 || data.local_port > 65535) {
        showNotification('本地端口必须在 1-65535 范围内', 'error');
        return;
    }
    
    if (data.remote_port && (data.remote_port < 1 || data.remote_port > 65535)) {
        showNotification('远程端口必须在 1-65535 范围内', 'error');
        return;
    }
    
    try {
        await apiRequest(`/api/proxies/${proxyId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        
        showNotification('代理更新成功', 'success');
        closeModal('editProxyModal');
        await loadProxiesForCurrentServer();
    } catch (error) {
        showNotification('更新失败: ' + error.message, 'error');
    }
}

// 复制到剪贴板
function copyToClipboard(elementId, successMessage = '已复制到剪贴板') {
    const element = document.getElementById(elementId);
    if (!element) {
        showNotification('未找到要复制的内容', 'error');
        return;
    }
    
    // 选择文本
    element.select();
    element.setSelectionRange(0, 99999); // 对于移动设备
    
    try {
        // 复制到剪贴板
        document.execCommand('copy');
        showNotification(successMessage, 'success');
    } catch (err) {
        // 备用方法：使用现代 API
        navigator.clipboard.writeText(element.value).then(() => {
            showNotification(successMessage, 'success');
        }).catch(() => {
            showNotification('复制失败，请手动复制', 'error');
        });
    }
}

// ==================== INI 转换功能 ====================

// 更新 API 帮助信息（使用真实地址）
function updateApiInfo() {
    // 获取当前访问的真实地址
    const protocol = window.location.protocol; // http: 或 https:
    const host = window.location.host; // 包含主机名和端口
    const apiUrl = `${protocol}//${host}`;
    
    // 更新 API URL 显示（使用 ID）
    const urlPlaceholder = document.getElementById('apiUrlPlaceholder');
    if (urlPlaceholder) {
        urlPlaceholder.textContent = apiUrl;
    }
    
    // 更新 API URL 显示（使用 class，批量更新）
    const urlElements = document.querySelectorAll('.apiUrlClass');
    urlElements.forEach(el => {
        el.textContent = apiUrl;
    });
    
    // 更新用户名显示
    const username = localStorage.getItem('username') || 'admin';
    
    // 使用 ID 的元素
    const apiUsername = document.getElementById('apiUsername');
    const usernameDisplay2 = document.getElementById('usernameDisplay2');
    const apiPassword = document.getElementById('apiPassword');
    
    if (apiUsername) {
        apiUsername.textContent = username;
    }
    if (usernameDisplay2) {
        usernameDisplay2.textContent = username;
    }
    if (apiPassword) {
        apiPassword.textContent = 'your_password';
    }
    
    // 使用 class 的元素（批量更新）
    const usernameElements = document.querySelectorAll('.apiUsernameClass');
    usernameElements.forEach(el => {
        el.textContent = username;
    });
}

// 兼容旧函数名
function updateApiUrlInHelp() {
    updateApiInfo();
}

// 复制 curl 命令
function copyCurlCommand() {
    const curlExample = document.getElementById('curlExample');
    if (!curlExample) {
        showNotification('无法找到命令内容', 'error');
        return;
    }
    
    // 获取命令文本（去除 HTML 标签）
    const commandText = curlExample.textContent || curlExample.innerText;
    
    // 复制到剪贴板
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(commandText).then(() => {
            showNotification('curl 命令已复制到剪贴板', 'success');
        }).catch(() => {
            showNotification('复制失败，请手动复制', 'error');
        });
    } else {
        // 备用方法
        const textarea = document.createElement('textarea');
        textarea.value = commandText;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showNotification('curl 命令已复制到剪贴板', 'success');
        } catch (err) {
            showNotification('复制失败，请手动复制', 'error');
        }
        document.body.removeChild(textarea);
    }
}

// 处理文件上传
async function handleFileUpload(event) {
    const file = event.target.files[0];
    
    if (!file) {
        return;
    }
    
    // 检查文件类型
    const validExtensions = ['.ini', '.txt', '.conf'];
    const fileName = file.name.toLowerCase();
    const isValidType = validExtensions.some(ext => fileName.endsWith(ext));
    
    if (!isValidType) {
        showNotification('请上传 .ini、.txt 或 .conf 格式的文件', 'error');
        event.target.value = ''; // 清空文件选择
        return;
    }
    
    // 检查文件大小 (限制 5MB)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
        showNotification('文件大小不能超过 5MB', 'error');
        event.target.value = '';
        return;
    }
    
    try {
        const text = await file.text();
        document.getElementById('iniContent').value = text;
        showNotification(`文件 "${file.name}" 已加载`, 'success');
    } catch (error) {
        showNotification('读取文件失败: ' + error.message, 'error');
        event.target.value = '';
    }
}

// 清空输入
function clearInput() {
    document.getElementById('iniContent').value = '';
    document.getElementById('iniFileInput').value = '';
    document.getElementById('tomlOutput').style.display = 'none';
    document.getElementById('tomlContent').value = '';
    showNotification('已清空', 'success');
}

// INI 转 TOML
async function convertIniToToml() {
    const iniContent = document.getElementById('iniContent').value.trim();
    
    if (!iniContent) {
        showNotification('请上传文件或输入 INI 配置内容', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/frpc/convert/ini-to-toml/direct', {
            method: 'POST',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'text/plain'
            },
            body: iniContent
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || 'Request failed');
        }
        
        const tomlContent = await response.text();
        
        // 显示结果
        document.getElementById('tomlContent').value = tomlContent;
        document.getElementById('tomlOutput').style.display = 'block';
        
        showNotification('转换成功！', 'success');
    } catch (error) {
        showNotification('转换失败: ' + error.message, 'error');
    }
}

// 下载 TOML 文件
function downloadToml() {
    const content = document.getElementById('tomlContent').value;
    
    if (!content) {
        showNotification('没有可下载的内容', 'error');
        return;
    }
    
    // 生成文件名（基于当前时间）
    const now = new Date();
    const timestamp = now.toISOString().slice(0, 19).replace(/:/g, '-');
    const fileName = `frpc_${timestamp}.toml`;
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showNotification('文件已下载: ' + fileName, 'success');
}

// 切换 curl 帮助显示/隐藏
function toggleCurlHelp() {
    const content = document.getElementById('curlHelpContent');
    const toggle = document.getElementById('curlHelpToggle');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.textContent = '▲';
    } else {
        content.style.display = 'none';
        toggle.textContent = '▼';
    }
}

// 复制 curl 示例到剪贴板
function copyCurlExample() {
    const token = localStorage.getItem('auth_token');
    const serverId = currentServerId || 1;
    const apiUrl = window.location.origin;
    
    // 获取当前服务器名称
    const currentServer = servers.find(s => s.id == serverId);
    const serverName = currentServer ? currentServer.name : 'server_name';
    
    // 构建最简洁的 curl 命令示例
    const curlExample = `# 方式 1: 最简洁（推荐，直接上传文件）
# URL 格式: /import/{格式}/{服务器名称}/{分组名称}
curl -u admin:admin -X POST \\
  -H "Content-Type: text/plain" \\
  --data-binary "@frpc.ini" \\
  ${apiUrl}/api/config/import/ini/${serverName}/production

# 不同的服务器和分组示例
curl -u admin:admin -X POST \\
  -H "Content-Type: text/plain" \\
  --data-binary "@frpc.ini" \\
  ${apiUrl}/api/config/import/ini/${serverName}/test

# TOML 格式示例
curl -u admin:admin -X POST \\
  -H "Content-Type: text/plain" \\
  --data-binary "@frpc.toml" \\
  ${apiUrl}/api/config/import/toml/${serverName}/production

# 方式 2: 使用项目脚本
./import_frpc_config.py frpc.ini --username admin --password admin

# 提示：
# - 将 frpc.ini 替换为你的配置文件路径
# - 将 ${serverName} 替换为实际的服务器名称
# - 将 production 替换为实际的分组名称`;
    
    // 复制到剪贴板
    navigator.clipboard.writeText(curlExample).then(() => {
        showNotification('curl 示例已复制到剪贴板', 'success');
    }).catch(err => {
        // 降级方案：使用 textarea
        const textarea = document.createElement('textarea');
        textarea.value = curlExample;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showNotification('curl 示例已复制到剪贴板', 'success');
        } catch (err) {
            showNotification('复制失败，请手动复制', 'error');
        }
        document.body.removeChild(textarea);
    });
}

// 显示 Token 信息
function showTokenInfo() {
    const token = localStorage.getItem('auth_token');
    
    if (!token) {
        showNotification('未找到 Token，请重新登录', 'error');
        return;
    }
    
    // 创建模态框显示 Token
    const modalHtml = `
        <div id="tokenInfoModal" class="modal" style="display: block;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h2>🔑 认证 Token</h2>
                    <span class="close-btn" onclick="closeModal('tokenInfoModal')">&times;</span>
                </div>
                <div style="padding: 1.5rem;">
                    <p style="color: #6b7280; margin-bottom: 1rem;">
                        您的认证 Token（请妥善保管，不要泄露）：
                    </p>
                    <div style="background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 0.375rem; font-family: 'Courier New', monospace; font-size: 0.9rem; word-break: break-all; margin-bottom: 1rem;">
                        ${token}
                    </div>
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <button class="btn btn-primary" onclick="copyTokenToClipboard()">
                            📋 复制 Token
                        </button>
                        <button class="btn btn-secondary" onclick="closeModal('tokenInfoModal')">
                            关闭
                        </button>
                    </div>
                    <div style="margin-top: 1rem; padding: 0.75rem; background: #fef3c7; border: 1px solid #fbbf24; border-radius: 0.375rem;">
                        <p style="margin: 0; color: #92400e; font-size: 0.875rem;">
                            💡 <strong>使用提示：</strong><br>
                            • 使用 Python 脚本：<code>./import_frpc_config.py frpc.ini --token "${token.substring(0, 20)}..."</code><br>
                            • 使用 Shell 脚本：<code>./import_frpc_config.sh frpc.ini "${token.substring(0, 20)}..."</code><br>
                            • 获取新 Token：<code>./get_token.sh</code>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除旧的模态框（如果存在）
    const oldModal = document.getElementById('tokenInfoModal');
    if (oldModal) {
        oldModal.remove();
    }
    
    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// 复制 Token 到剪贴板
function copyTokenToClipboard() {
    const token = localStorage.getItem('auth_token');
    
    if (!token) {
        showNotification('未找到 Token', 'error');
        return;
    }
    
    navigator.clipboard.writeText(token).then(() => {
        showNotification('Token 已复制到剪贴板', 'success');
    }).catch(err => {
        // 降级方案
        const textarea = document.createElement('textarea');
        textarea.value = token;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showNotification('Token 已复制到剪贴板', 'success');
        } catch (err) {
            showNotification('复制失败，请手动复制', 'error');
        }
        document.body.removeChild(textarea);
    });
}

