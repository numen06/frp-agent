# VSCode 开发环境配置

本目录包含 VSCode 的开发环境配置文件。

## 快速开始

### 1. 安装环境

**Windows:**
```powershell
.\setup_env.ps1
```

**Linux/macOS:**
```bash
chmod +x setup_env.sh
./setup_env.sh
```

### 2. 安装推荐的 VSCode 扩展

VSCode 会自动提示安装推荐的扩展，或手动安装：

**Python 开发:**
- Python
- Pylance
- Black Formatter
- debugpy
- Flake8

**前端开发:**
- ESLint
- Volar (Vue 3 支持)
- TypeScript Vue Plugin
- Prettier
- Tailwind CSS IntelliSense

### 3. 开始调试

1. 按 `F5` 开始调试
2. 或使用调试面板选择配置：

**Python 调试配置:**
   - **Python: FastAPI 应用** - 调试主应用
   - **Python: app.py** - 调试 app.py
   - **Python: 当前文件** - 调试当前打开的 Python 文件
   - **Python: 导入配置脚本** - 调试配置导入脚本

**Node.js/前端调试配置:**
   - **Node.js: 调试 Vite 开发服务器** - 调试 Vite 开发服务器
   - **Node.js: 调试当前文件** - 调试当前打开的 Node.js 文件
   - **Chrome: 调试前端应用** - 在 Chrome 中调试前端应用（需要先启动 Vite 服务器）
   - **Edge: 调试前端应用** - 在 Edge 中调试前端应用（需要先启动 Vite 服务器）
   - **复合: 前后端同时调试** - 同时启动并调试前后端应用

## 任务 (Tasks)

使用 `Ctrl+Shift+P` (Windows/Linux) 或 `Cmd+Shift+P` (macOS)，输入 "Tasks: Run Task" 运行以下任务：

**Python 任务:**
- **安装 Python 依赖** - 安装 requirements.txt 中的依赖
- **初始化数据库** - 运行数据库初始化脚本
- **运行 FastAPI 应用** - 启动开发服务器（端口 8000）
- **运行 app.py** - 运行 app.py 文件
- **安装开发依赖** - 安装依赖和调试工具

**Node.js/前端任务:**
- **安装 Node.js 依赖** - 安装 frontend/package.json 中的依赖
- **运行前端开发服务器** - 启动 Vite 开发服务器（端口 5173）
- **构建前端应用** - 构建生产版本
- **预览构建结果** - 预览构建后的应用

**组合任务:**
- **安装所有依赖** - 并行安装 Python 和 Node.js 依赖

## 配置文件说明

- `launch.json` - 调试配置
- `tasks.json` - 任务配置
- `settings.json` - 工作区设置
- `extensions.json` - 推荐的扩展列表

## 调试技巧

### 前后端联合调试

1. **方式一：使用复合调试配置**
   - 选择 "复合: 前后端同时调试" 配置
   - 按 `F5` 启动，会自动启动后端、前端和浏览器调试

2. **方式二：分别启动**
   - 先运行任务 "运行 FastAPI 应用" 启动后端
   - 再运行任务 "运行前端开发服务器" 启动前端
   - 最后选择 "Chrome: 调试前端应用" 或 "Edge: 调试前端应用" 进行浏览器调试

### 断点调试

- **Python**: 在代码中设置断点，使用 Python 调试配置即可
- **JavaScript/Vue**: 在 `.vue` 或 `.js` 文件中设置断点，使用浏览器调试配置
- **Node.js**: 在 Node.js 文件中设置断点，使用 Node.js 调试配置

## 注意事项

1. **Python 环境**
   - 确保已创建并激活虚拟环境
   - 首次使用前运行环境安装脚本
   - 如果遇到导入错误，检查 `PYTHONPATH` 设置

2. **Node.js 环境**
   - 确保已安装 Node.js 18+ 和 npm
   - 前端依赖安装在 `frontend` 目录下
   - Vite 开发服务器默认运行在 `http://localhost:5173`

3. **端口占用**
   - 后端 API: `http://localhost:8000`
   - 前端开发服务器: `http://localhost:5173`
   - 确保这些端口未被占用

4. **PowerShell 执行策略问题（Windows）**
   - 如果遇到 "PSSecurityException" 错误，任务已配置为使用 `cmd.exe` 执行
   - 如需修复 PowerShell 执行策略，可运行 `.\fix_powershell_policy.ps1`
   - 或者手动设置：`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

