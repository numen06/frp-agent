# 移动端优化验证记录

> 验证日期：2026-05-26  
> 构建命令：`cd frontend && npm run build`  
> 构建结果：**通过**（Vite 5.4.21，167 模块，约 3.3s）

## 改动范围摘要

| 子任务 | 状态 | 主要文件 |
|--------|------|----------|
| 1 基线审计 | ✅ | `frontend/MOBILE-AUDIT.md` |
| 2 全局布局 | ✅ | `Layout.vue`、`index.css` |
| 3 通用组件 | ✅ | `AppSelect`、`TableSearch`、`TablePagination`、`ServerSelector` |
| 4 列表卡片视图 | ✅ | `ProxyList`、`ServerManagePage`、`ApiKeysPage`、`PackageManagePage`、`GroupManage`、`GroupProxiesDialog`、`ServerManageDialog` |
| 5 工具条/筛选/批量 | ✅ | `ProxyList` sticky 批量条、筛选 `w-full`、下拉视口约束 |
| 6 弹窗适配 | ✅ | 全部计划内弹窗使用 `items-end sm:items-center` + 近全屏/可滚动 footer |
| 7 Dashboard/INI/Login | ✅ | `Dashboard.vue`、`IniConverter.vue`、`CodeEditor.vue`、`Login.vue` |
| 8 构建与回归 | ✅ | 本文档 |

## 设计模式

- **断点**：`< md`（768px）为手机端；`hidden md:block` / `md:hidden` 切换表格与卡片。
- **触控**：`.touch-target`（40px）、主按钮 `min-h-10`/`min-h-11`（44px）。
- **弹窗**：`h-[calc(100dvh-1rem)] sm:h-auto`、`rounded-t-xl sm:rounded-xl`、footer 手机端 `w-full`。
- **溢出**：列表长文本 `break-all`/`truncate`；壳层 `overflow-x-hidden`。

## 构建验证

```
cd frontend && npm run build
# Exit code: 0
```

## 本地预览

```bash
cd frontend && npm run dev -- --host 127.0.0.1
```

浏览器 DevTools → 设备工具栏，建议视口：

| 视口 | 场景 |
|------|------|
| 360×800 | 低宽安卓 |
| 375×812 | iPhone SE |
| 390×844 | 常见 iPhone |
| 430×932 | 大屏手机 |
| 768×1024 | 平板竖屏 |

## 路由检查清单

在控制台执行（应返回 `true`）：

```javascript
document.documentElement.scrollWidth <= window.innerWidth
```

| 路由 | 检查项 | 预期 |
|------|--------|------|
| `/login` | 表单宽度、登录按钮可点 | 无横向滚动，键盘可提交 |
| `/dashboard` | 统计 2 列、服务器卡片 | 首屏无横向滚动 |
| `/proxies` | 卡片、筛选、sticky 批量、分页 | 360px 可操作 |
| `/groups` | 分组卡片、弹窗 | 更多菜单不溢出 |
| `/servers` | 服务器卡片、添加/编辑弹窗 | footer 按钮可见 |
| `/api-keys` | 密钥 break-all、创建弹窗 | 长密钥不撑宽 |
| `/packages` | 安装包卡片、上传/同步弹窗 | 筛选纵向排列 |
| `/converter` | INI 编辑器高度、转换/复制 | 390px 可完成粘贴转换 |

## 弹窗抽检

打开以下弹窗后再次执行 `scrollWidth <= innerWidth`，并确认正文可滚动、底部按钮可触达：

- 添加/编辑代理（`ProxyDialog`）
- 导入配置、生成配置
- 安装包上传/同步/脚本生成
- API Key 创建/编辑
- 用户管理、分组部署/导入

## 已知限制

- 未纳入 Playwright 视觉回归；依赖构建 + 人工视口检查。
- 极长未断行 URL（外部粘贴）仍可能在个别 `pre` 内横向滚动（容器内滚动，非页面级）。
- 桌面端表格与批量流程保持原样，仅 `< md` 切换为卡片/简化分页。

## 自动检查脚本（可选）

在任意已登录页面控制台：

```javascript
(() => {
  const ok = document.documentElement.scrollWidth <= window.innerWidth;
  console.log(ok ? '✓ 无页面级横向溢出' : '✗ 存在横向溢出', {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth
  });
  return ok;
})();
```
