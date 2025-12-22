# frp-agent 后端

基于 FastAPI 的后端 API 服务。

## 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（主入口文件，推荐）
python app.py

# 或使用 uvicorn（需要在 backend 目录下）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**注意**：主入口文件是 `app.py`，它会自动处理路径配置和环境检测。

## 环境变量

创建 `.env` 文件配置环境变量：

```bash
AUTH_USERNAME=admin
AUTH_PASSWORD=admin
DATABASE_URL=sqlite:///./data/frp_agent.db
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
```

## API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs (如果启用)
- ReDoc: http://localhost:8000/redoc (如果启用)

## 技术栈

- FastAPI
- SQLAlchemy
- SQLite
- APScheduler

