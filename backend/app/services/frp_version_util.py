"""FRP 版本解析与比较"""
import re
from typing import List, Optional, Tuple

_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")


def parse_version(raw: Optional[str]) -> Optional[Tuple[int, ...]]:
    """从版本字符串解析 (major, minor, patch)，无法解析时返回 None。"""
    if not raw:
        return None
    m = _VERSION_RE.search(raw.strip())
    if not m:
        return None
    parts = m.group(1).split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def normalize_version_display(raw: Optional[str]) -> Optional[str]:
    parsed = parse_version(raw)
    if parsed:
        return ".".join(str(p) for p in parsed)
    return raw.strip() if raw else None


def compare_versions(current: Optional[str], target: Optional[str]) -> int:
    """比较版本：current < target 返回 -1，相等 0，current > target 返回 1。无法解析时返回 0。"""
    c = parse_version(current)
    t = parse_version(target)
    if c is None or t is None:
        return 0
    if c < t:
        return -1
    if c > t:
        return 1
    return 0


def is_upgradeable(current: Optional[str], target: Optional[str]) -> bool:
    return compare_versions(current, target) < 0


def version_sort_key(tag: str) -> tuple:
    if not tag:
        return (0,)
    s = tag.strip().lstrip("vV")
    parts = []
    for part in re.split(r"[.\-]", s):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(0)
    return tuple(parts)


def sort_versions_desc(versions: List[str]) -> List[str]:
    return sorted({x for x in versions if x}, key=version_sort_key, reverse=True)
