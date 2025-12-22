# frp-agent 启动指南

## ⚠️ 重要提示

**主入口文件**：`backend/app.py`

**不要**从项目根目录直接运行 `uvicorn app.main:app`，这会因为找不到 `app` 模块而失败。

## ✅ 正确的启动方式

### 方式 1：使用主入口文件（推荐）

```bash
# 进入 backend 目录
cd backend

# 运行主入口文件
python app.py
```

### 方式 2：从项目根目录运行辅助脚本

```bash
# 在项目根目录
python run.py
```

### 方式 3：直接运行主入口文件（从项目根目录）

```bash
# 在项目根目录
python backend/app.py
```

### 方式 4：使用 uvicorn（需要在 backend 目录下）

```bash
# 进入 backend 目录
cd backend

# 运行 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## ❌ 错误的启动方式

```bash
# ❌ 错误：从项目根目录直接运行 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 错误原因：Python 无法找到 app 模块（它在 backend/app/ 目录下）
```

## 🔧 调试配置

如果使用 VSCode 调试，请配置 `launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: frp-agent",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/app.py",
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

或者使用模块方式：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: uvicorn",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ],
            "cwd": "${workspaceFolder}/backend",
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

## 📝 说明

- `backend/app.py` 是主入口文件，会自动处理路径配置和环境检测
- `run.py` 是辅助脚本，用于从项目根目录启动
- 主入口文件支持自动检测运行环境（本地开发/Docker）
- 主入口文件会自动设置 Python 路径和 PYTHONPATH 环境变量

