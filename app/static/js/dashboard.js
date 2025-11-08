// 仪表板脚本

let servers = [];
let proxies = [];
let currentServerId = null;

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
        currentServerId = servers[0].id;
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
        renderProxiesTable();
        updateStats();
        return;
    }
    
    try {
        const allProxies = await apiRequest('/api/proxies');
        proxies = allProxies.filter(p => p.frps_server_id == currentServerId);
        renderProxiesTable();
        updateStats();
    } catch (error) {
        showNotification('加载代理失败: ' + error.message, 'error');
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
        container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">暂无代理配置</p>';
        return;
    }
    
    const html = `
        <table>
            <thead>
                <tr>
                    <th>名称</th>
                    <th>类型</th>
                    <th>远程端口</th>
                    <th>本地地址</th>
                    <th>状态</th>
                    <th>更新时间</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                ${proxies.map(proxy => `
                    <tr>
                        <td>${proxy.name}</td>
                        <td>${proxy.proxy_type.toUpperCase()}</td>
                        <td>${formatPort(proxy.remote_port)}</td>
                        <td>${proxy.local_ip}:${proxy.local_port}</td>
                        <td>${statusBadge(proxy.status)}</td>
                        <td>${formatDateTime(proxy.updated_at)}</td>
                        <td>
                            <button class="btn btn-danger btn-small" onclick="deleteProxy(${proxy.id})">删除</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

// 更新统计数据
function updateStats() {
    const onlineCount = proxies.filter(p => p.status === 'online').length;
    const offlineCount = proxies.filter(p => p.status === 'offline').length;
    
    document.getElementById('proxyCount').textContent = proxies.length;
    document.getElementById('onlineCount').textContent = onlineCount;
    document.getElementById('offlineCount').textContent = offlineCount;
    document.getElementById('portCount').textContent = proxies.filter(p => p.remote_port).length;
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
            currentServerId = newServer.id;
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

