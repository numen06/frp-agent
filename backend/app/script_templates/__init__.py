"""外置 shell / PowerShell / systemd 片段，与加载器同目录（便于归类与打包）。"""
from functools import lru_cache
from pathlib import Path

_SCRIPT_TEMPLATES_DIR = Path(__file__).resolve().parent

_TEMPLATE_SUFFIXES = frozenset({".sh", ".ps1", ".unit"})


def list_script_template_names() -> list[str]:
    """返回包内脚本模板文件名（不含 __init__.py）。"""
    return sorted(
        p.name
        for p in _SCRIPT_TEMPLATES_DIR.iterdir()
        if p.is_file() and p.suffix in _TEMPLATE_SUFFIXES
    )


@lru_cache(maxsize=64)
def load_shell_template(name: str) -> str:
    p = _SCRIPT_TEMPLATES_DIR / name
    if not p.is_file():
        raise FileNotFoundError(str(p))
    return p.read_text(encoding="utf-8")
