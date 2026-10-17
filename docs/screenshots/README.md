# 截图与移动端验证

此目录的 PNG 使用当前生产构建和独立演示接口生成，尺寸均为 **1920 × 1080**、设备像素比 1，未拉伸或拼接。示例地址使用 `example.com`、`192.0.2.0/24` 和虚构内网地址，所有密钥均为不可用演示值。

脚本拦截所有 API 请求，未知接口会失败，外部请求会被阻止；不需要启动后端，不读取或修改真实数据库。

```bash
cd frontend
npm ci
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
```

在另一个终端，从仓库根目录运行：

```bash
python -m pip install playwright==1.58.0
python -m playwright install chromium
python frontend/scripts/capture_screenshots.py
```

除桌面截图外，脚本检查 320 / 390 / 768 / 1280px 页面宽度、手机导航、主要弹窗的滚动与关闭，以及 420px 可视高度下的操作按钮可达性。移动端验证图片输出到被 Git 忽略的 `data/ui-review`。

缩小视口用于模拟键盘占用空间，不能替代 iOS / Android 真机的软键盘验收。
