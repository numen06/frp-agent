# frp-client install script (PowerShell)
# platform: {{platform}}  version: {{version}}

$ErrorActionPreference = 'Stop'
$FRP_DIR = 'C:\frp'
$FRPC_EXE = "$FRP_DIR\frpc.exe"

# --- 创建目录 ---
New-Item -ItemType Directory -Force -Path $FRP_DIR | Out-Null

# --- 下载并解压 frpc ---
Write-Host "Downloading {{filename}} ..."
Invoke-WebRequest -Uri "{{download_url}}" -OutFile "$env:TEMP\{{filename}}"
tar -xf "$env:TEMP\{{filename}}" -C "$env:TEMP"
Copy-Item "$env:TEMP\frp_*\frpc.exe" $FRPC_EXE -Force

# --- 清理临时文件 ---
Remove-Item "$env:TEMP\{{filename}}" -Force -ErrorAction SilentlyContinue
Get-ChildItem "$env:TEMP\frp_*" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# --- 配置文件（仅当不存在时下载，不覆盖已有配置）---
{{config_line}}

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

Write-Host "=== Frp Client 部署完成 ==="
Write-Host "安装路径: $FRPC_EXE"
