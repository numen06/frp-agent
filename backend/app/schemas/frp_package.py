"""FRP 安装包相关 schemas"""
from datetime import datetime
from typing import Optional, List, Literal
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


class FrpPackagePaginatedResponse(BaseModel):
    """安装包列表分页响应"""

    items: List[FrpPackageResponse]
    total: int
    page: int
    page_size: int


class FrpPackageSyncRequest(BaseModel):
    version: str = Field(..., min_length=1, max_length=50)
    platforms: Optional[List[str]] = None
    download_source: Literal["origin", "accelerated"] = "origin"


class PackageSyncJobResultItem(BaseModel):
    platform: str
    filename: str
    status: str
    message: Optional[str] = None
    package_id: Optional[int] = None


class PackageSyncJobResponse(BaseModel):
    job_id: str
    status: str
    version: str
    platforms: List[str] = []
    download_source: str
    total: int
    completed: int
    results: List[PackageSyncJobResultItem] = []
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class PackageSyncJobCreatedResponse(BaseModel):
    job_id: str
    status: str
    total: int
    completed: int = 0
    message: str = "同步任务已创建，正在后台下载"


class FrpPackageInstallScriptRequest(BaseModel):
    package_id: int
    install_path: str = "/usr/local/bin"
    config_url: Optional[str] = None
