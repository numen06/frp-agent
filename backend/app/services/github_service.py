"""GitHub releases 服务"""
import os
import re
import hashlib
from typing import List, Dict, Optional, Set
import httpx

from app.config import get_settings


# 官方 frp Release 资源命名：frp_<semver>_<os_arch>.<tar.gz|zip|...>
# 平台段随官方发布变化（含 mips、riscv 等），不从代码写死枚举。
_FRP_ASSET_NAME_RE = re.compile(
    r"^frp_\d+\.\d+\.\d+_(.+)\.(?:tar\.gz|tgz|zip|tar\.xz)$",
    re.IGNORECASE,
)


class GithubService:
    REPO_API = "https://api.github.com/repos/fatedier/frp/releases"

    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "frp-agent",
        }
        if self.settings.github_api_token:
            self.headers["Authorization"] = f"Bearer {self.settings.github_api_token}"

    async def fetch_releases(self) -> List[Dict]:
        async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
            resp = await client.get(self.REPO_API)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def parse_platform_from_filename(filename: str) -> Optional[str]:
        if not filename or filename.endswith(".sha256"):
            return None
        m = _FRP_ASSET_NAME_RE.match(filename.strip())
        if not m:
            return None
        return m.group(1)

    @staticmethod
    def discover_platforms_from_release(release: Dict) -> List[str]:
        """从单个 Release 的 assets 文件名解析出官方提供的平台标识列表。"""
        seen: Set[str] = set()
        for asset in release.get("assets") or []:
            name = asset.get("name") or ""
            p = GithubService.parse_platform_from_filename(name)
            if p:
                seen.add(p)
        return sorted(seen)

    async def discover_platforms_for_tag(self, tag_name: str) -> List[str]:
        releases = await self.fetch_releases()
        rel = next((x for x in releases if x.get("tag_name") == tag_name), None)
        if not rel:
            return []
        return self.discover_platforms_from_release(rel)

    async def download_asset(self, url: str, save_path: str) -> int:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        async with httpx.AsyncClient(timeout=120.0, headers=self.headers, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                size = 0
                with open(save_path, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            f.write(chunk)
                            size += len(chunk)
                return size

    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                block = f.read(1024 * 1024)
                if not block:
                    break
                sha256.update(block)
        return sha256.hexdigest()
