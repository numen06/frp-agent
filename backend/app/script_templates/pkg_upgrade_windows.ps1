# frp-client upgrade script (PowerShell)
# platform: {{platform}}  version: {{version}}

$ErrorActionPreference = 'Stop'
$FRP_DIR = 'C:\frp'
$FRPC_EXE = "$FRP_DIR\frpc.exe"

# --- 检查是否已安装 ---
if (-not (Test-Path $FRPC_EXE)) {
    Write-Host "错误: 未检测到已安装的 frpc ($FRPC_EXE)，请先使用安装脚本进行安装。"
    exit 1
}

$OLD_VERSION = & $FRPC_EXE --version 2>&1
Write-Host "当前版本: $OLD_VERSION"
Write-Host "目标版本: {{version}}"

# --- 停止 frpc 服务（如已注册为系统服务）---
if (Get-Service -Name frpc -ErrorAction SilentlyContinue) {
    Write-Host "停止 frpc 服务..."
    Stop-Service -Name frpc -Force
}

# --- 备份当前 frpc ---
if (Test-Path $FRPC_EXE) {
    $BACKUP = "$FRP_DIR\frpc.exe.bak"
    Copy-Item $FRPC_EXE $BACKUP -Force
    Write-Host "已备份当前版本: $BACKUP"
}

# --- 下载并替换 ---
Write-Host "下载 {{filename}} ..."
Invoke-WebRequest -Uri "{{download_url}}" -OutFile "$env:TEMP\{{filename}}"
tar -xf "$env:TEMP\{{filename}}" -C "$env:TEMP"
Copy-Item "$env:TEMP\frp_*\frpc.exe" $FRPC_EXE -Force

# --- 清理临时文件 ---
Remove-Item "$env:TEMP\{{filename}}" -Force -ErrorAction SilentlyContinue
Get-ChildItem "$env:TEMP\frp_*" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# --- 配置兼容性：frpc.ini -> frpc.toml 迁移 ---
$INI_FILE = "$FRP_DIR\frpc.ini"
$TOML_FILE = "$FRP_DIR\frpc.toml"
if (Test-Path $INI_FILE) {
    if (-not (Test-Path $TOML_FILE)) {
        Write-Host "迁移到 TOML: 将 $INI_FILE 重命名为 $TOML_FILE"
        Move-Item $INI_FILE $TOML_FILE
    } else {
        $ts = Get-Date -Format 'yyyyMMdd_HHmmss'
        Move-Item $INI_FILE "$INI_FILE.backup_$ts"
        Write-Host "警告: $INI_FILE 存在但 $TOML_FILE 已存在，已备份为 $INI_FILE.backup_$ts"
    }
}

# --- 重启 frpc 服务 ---
if (Get-Service -Name frpc -ErrorAction SilentlyContinue) {
    Write-Host "启动 frpc 服务..."
    Start-Service -Name frpc
}

$NEW_VERSION = & $FRPC_EXE --version 2>&1
Write-Host "=== Frp Client 升级完成 ==="
Write-Host "版本: $OLD_VERSION -> $NEW_VERSION"
Write-Host "安装路径: $FRPC_EXE"
