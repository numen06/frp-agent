import sys
from pathlib import Path

# 将 backend 目录加入 path，便于 `from app...` 导入
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
