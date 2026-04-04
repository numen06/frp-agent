# frpc 启动脚本 (PowerShell)

$FrpcPath = "@@FRPC_PATH@@"
$ConfigPath = "@@CONFIG_PATH@@"
$LogFile = "frpc.log"

function Start-Frpc {
    $processes = Get-Process -Name frpc -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "frpc 已经在运行中 (PID: $($processes.Id))"
        return
    }

    Write-Host "启动 frpc..."
    Start-Process -FilePath $FrpcPath -ArgumentList "-c", $ConfigPath -RedirectStandardOutput $LogFile -WindowStyle Hidden
    Write-Host "frpc 已启动"
}

function Stop-Frpc {
    $processes = Get-Process -Name frpc -ErrorAction SilentlyContinue
    if (-not $processes) {
        Write-Host "frpc 未运行"
        return
    }

    Write-Host "停止 frpc (PID: $($processes.Id))..."
    Stop-Process -Name frpc -Force
    Write-Host "frpc 已停止"
}

function Get-FrpcStatus {
    $processes = Get-Process -Name frpc -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "frpc 正在运行 (PID: $($processes.Id))"
    } else {
        Write-Host "frpc 未运行"
    }
}

# 主逻辑
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

switch ($Action) {
    "start" {
        Start-Frpc
    }
    "stop" {
        Stop-Frpc
    }
    "restart" {
        Stop-Frpc
        Start-Sleep -Seconds 2
        Start-Frpc
    }
    "status" {
        Get-FrpcStatus
    }
}
