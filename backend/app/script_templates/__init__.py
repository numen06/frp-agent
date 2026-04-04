"""外置 shell / PowerShell / systemd 片段，与加载器同目录（便于归类与打包）。"""
from functools import lru_cache
from pathlib import Path

_SCRIPT_TEMPLATES_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=64)
def load_shell_template(name: str) -> str:
    p = _SCRIPT_TEMPLATES_DIR / name
    if not p.is_file():
        raise FileNotFoundError(str(p))
    return p.read_text(encoding="utf-8")
