"""从本地 frp 安装包提取 frpc 二进制"""
import os
import re
import shutil
import tarfile
import tempfile
import zipfile
from typing import Optional

from app.models.frp_package import FrpPackage


def _resolve_package_path(file_path: str) -> str:
    if os.path.isabs(file_path) and os.path.exists(file_path):
        return file_path
    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(os.path.dirname(current_file))
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)
    candidate = os.path.join(project_root, file_path)
    if os.path.exists(candidate):
        return candidate
    if os.path.exists(file_path):
        return file_path
    raise FileNotFoundError(f"安装包文件不存在: {file_path}")


def extract_frpc_binary(package: FrpPackage) -> str:
    """解压安装包并返回本地 frpc 二进制路径（调用方负责清理临时目录的父级）。"""
    src = _resolve_package_path(package.file_path)
    tmp_dir = tempfile.mkdtemp(prefix="frpc_extract_")
    lower = src.lower()
    frpc_path: Optional[str] = None

    if lower.endswith((".tar.gz", ".tgz")):
        with tarfile.open(src, "r:gz") as tar:
            for member in tar.getmembers():
                base = os.path.basename(member.name)
                if base == "frpc" and member.isfile():
                    tar.extract(member, tmp_dir)
                    frpc_path = os.path.join(tmp_dir, member.name)
                    break
    elif lower.endswith(".zip"):
        with zipfile.ZipFile(src, "r") as zf:
            for name in zf.namelist():
                if name.endswith("/frpc") or name.endswith("\\frpc") or name == "frpc":
                    zf.extract(name, tmp_dir)
                    frpc_path = os.path.join(tmp_dir, name)
                    break
    else:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError(f"不支持的安装包格式: {src}")

    if not frpc_path or not os.path.isfile(frpc_path):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise FileNotFoundError("安装包中未找到 frpc 二进制")

    # 将 frpc 移到 tmp_dir 根目录便于上传
    final_path = os.path.join(tmp_dir, "frpc")
    if os.path.abspath(frpc_path) != os.path.abspath(final_path):
        shutil.move(frpc_path, final_path)
    os.chmod(final_path, 0o755)
    return final_path


def cleanup_extract_dir(frpc_path: str) -> None:
    parent = os.path.dirname(frpc_path)
    if parent and "frpc_extract_" in parent:
        shutil.rmtree(parent, ignore_errors=True)
