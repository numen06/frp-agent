// API 基础配置
const API_BASE = '';

// 获取认证 token
function getAuthHeader() {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        // 如果没有 token，重定向到登录页
        window.location.href = '/login';
        return '';
    }
    return 'Basic ' + token;
}

// 通用 API 请求函数
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Authorization': getAuthHeader(),
            'Content-Type': 'application/json',
        },
    };
    
    const response = await fetch(API_BASE + url, {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    });
    
    // 如果返回 401，说明认证失败，跳转到登录页
    if (response.status === 401) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('username');
        window.location.href = '/login';
        return;
    }
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || 'Request failed');
    }
    
    if (response.status === 204) {
        return null;
    }
    
    return response.json();
}

// 为了兼容旧代码，保留 AUTH_HEADER 常量
const AUTH_HEADER = getAuthHeader();

// 显示通知
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        border-radius: 5px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 2000;
        animation: slideIn 0.3s;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Modal 控制
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

// 格式化端口
function formatPort(port) {
    return port || '-';
}

// 生成状态徽章
function statusBadge(status) {
    const badgeClass = status === 'online' ? 'badge-online' : 'badge-offline';
    const text = status === 'online' ? '在线' : '离线';
    return `<span class="badge ${badgeClass}">${text}</span>`;
}

// 页面加载动画
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading"><div class="spinner"></div><p>加载中...</p></div>';
    }
}

// 动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

