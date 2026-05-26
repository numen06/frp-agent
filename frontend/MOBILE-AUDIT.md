# 移动端基线审计清单

> 审计范围：`frontend/src/views`、`frontend/src/components`、`frontend/src/assets/index.css`  
> 验收视口：360×800、375×812、390×844、430×932、768×1024

## 全局风险模式

| 模式 | 影响 | 优先级 |
|------|------|--------|
| 宽表格无卡片替代 | 页面级横向滚动 | P0 |
| `style="width: 250px"` 固定宽度筛选 | 小屏挤压/溢出 | P0 |
| `absolute right-0` 下拉菜单 | 菜单超出视口右侧 | P1 |
| `items-center justify-center` 居中弹窗 | 键盘弹出时 footer 不可达 | P1 |
| 操作按钮 `h-8` / `py-1.5` | 触控区域不足 40px | P1 |
| 长密钥/API URL 无 `break-all` | 撑破容器 | P1 |
| 导航 `flex-wrap` 折行不稳定 | 360px 下 header/nav 拥挤 | P2 |

## 分页面问题清单

### Layout.vue
- **P0**：主体 `px-4 py-6` 在小屏偏宽；导航折行后当前路由不够清晰。
- **P1**：移动端 nav 应横向滚动 tabs；路由切换后应收起折叠菜单。
- **P1**：通知/用户下拉已部分约束 `w-[calc(100vw-2rem)]`，需保持。
- **P2**：footer 分隔符 `|` 在极窄屏拥挤，应纵向排列。

### Dashboard.vue
- **P1**：欢迎区统计已 2 列，基本可用。
- **P0**：服务器详情表格在 <768px 需卡片视图（已修复）。
- **P2**：快速操作按钮文字换行需验证。

### ProxyList.vue
- **P0**：10 列表格导致横向滚动，需 `md:hidden` 卡片 + `hidden md:block` 表格。
- **P0**：筛选区 `width: 250px` 固定宽度。
- **P1**：顶部 6+ 操作按钮挤在一行。
- **P1**：批量操作条占首屏过多，宜 sticky 底部。
- **P1**：批量/添加下拉 `absolute right-0` 可能溢出。

### GroupManage.vue / GroupManagePage.vue
- **P0**：分组表格无移动端卡片。
- **P1**：顶部 3 按钮 + 搜索 `min-w-[200px]` 挤压。
- **P1**：更多操作 Teleport 菜单需视口约束。

### ServerManagePage.vue
- **已修复**：卡片视图 + 响应式工具栏 + 近全屏弹窗。

### ApiKeysPage.vue
- **已修复**：卡片视图 + 密钥 `break-all` + 40px 操作按钮。

### PackageManagePage.vue
- **P0**：安装包表格无卡片视图。
- **P1**：顶部 5 按钮 + 更多菜单溢出风险。
- **P2**：筛选区已为 `grid-cols-1 md:grid-cols-3`，基本可用。

### IniConverterPage.vue / IniConverter.vue
- **P1**：Tab 标签文字在小屏可能换行难看。
- **P1**：CodeEditor 高度 280px 在矮屏需 `min()` 自适应。
- **P1**：上传+清空按钮行需纵向堆叠。
- **P2**：命令行 `pre` 需 `break-all`。

### Login.vue
- **P2**：表单基本 responsive；输入框/登录按钮需 `min-h-10` 触控高度。

### 弹窗组件（ProxyDialog、ImportConfigDialog 等）
- **P1**：多数使用居中弹窗，手机端应 `items-end sm:items-center` + `h-[calc(100dvh-1rem)]`。
- **P1**：footer 按钮手机端应 `w-full` 或两列。
- **P2**：关闭/危险按钮补 `aria-label`。

### 通用组件
- **TablePagination**：页码过多挤在一行 → 手机端简化为 prev/页码/next + page size 两行布局。
- **TableSearch**：已 40px 高度 + 清除按钮 aria-label。
- **AppSelect**：已 `min-width: 0`；`w-full` 场景需 block 容器。
- **ServerSelector**：label/select/按钮应纵向堆叠。

## 修复优先级总结

1. **P0（必须先做）**：ProxyList、PackageManagePage、GroupManage 卡片视图；ProxyList 筛选固定宽；Layout 导航/间距。
2. **P1（本次完成）**：弹窗移动端模式统一；工具栏/批量区响应式；TablePagination；ServerSelector。
3. **P2（ polish）**：Login 触控高度；IniConverter 细节；视觉一致性。
