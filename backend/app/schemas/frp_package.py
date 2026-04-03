"""FRP 安装包相关 schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FrpPackageResponse(BaseModel):
    id: int
    version: str
    platform: str
    filename: str
    file_size: int
    source: str
    download_url: Optional[str]
    is_active: bool
    downloaded_at: datetime
    sha256_checksum: Optional[str]

    class Config:
        from_attributes = True


class FrpPackageSyncRequest(BaseModel):
    version: str = Field(..., min_length=1, max_length=50)
    platforms: Optional[List[str]] = None


class FrpPackageInstallScriptRequest(BaseModel):
    package_id: int
    install_path: str = "/usr/local/bin"
    config_url: Optional[str] = None
