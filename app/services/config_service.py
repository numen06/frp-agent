"""配置生成服务"""
from typing import List, Optional
import toml
from sqlalchemy.orm import Session

from app.models.frps_server import FrpsServer
from app.schemas.config import ProxyConfig


class ConfigService:
    """配置生成服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_frpc_toml(
        self,
        server: FrpsServer,
        proxies: List[ProxyConfig],
        user_token: Optional[str] = None,
        use_encryption: bool = False,
        use_compression: bool = False
    ) -> str:
        """生成 frpc.toml 配置文件
        
        Args:
            server: frps 服务器配置
            proxies: 代理配置列表
            user_token: 用户令牌（可选）
            use_encryption: 是否使用加密
            use_compression: 是否使用压缩
            
        Returns:
            frpc.toml 配置内容
        """
        config = {}
        
        # 基础配置
        config["serverAddr"] = server.server_addr
        config["serverPort"] = server.server_port
        
        if user_token:
            config["auth"] = {
                "method": "token",
                "token": user_token
            }
        
        # 传输设置
        transport = {}
        if use_encryption or use_compression:
            if use_encryption:
                transport["useEncryption"] = True
            if use_compression:
                transport["useCompression"] = True
            config["transport"] = transport
        
        # 代理配置
        proxies_config = []
        for proxy in proxies:
            proxy_conf = {
                "name": proxy.name,
                "type": proxy.type,
                "localIP": proxy.local_ip,
                "localPort": proxy.local_port,
            }
            
            # TCP/UDP 需要 remotePort
            if proxy.type in ["tcp", "udp"] and proxy.remote_port:
                proxy_conf["remotePort"] = proxy.remote_port
            
            # HTTP/HTTPS 需要域名配置
            if proxy.type in ["http", "https"]:
                if proxy.custom_domains:
                    proxy_conf["customDomains"] = proxy.custom_domains
                if proxy.subdomain:
                    proxy_conf["subdomain"] = proxy.subdomain
            
            proxies_config.append(proxy_conf)
        
        config["proxies"] = proxies_config
        
        # 转换为 TOML 格式
        toml_content = toml.dumps(config)
        
        return toml_content
    
    def generate_startup_script_linux(
        self,
        frpc_path: str = "./frpc",
        config_path: str = "./frpc.toml"
    ) -> str:
        """生成 Linux 启动脚本
        
        Args:
            frpc_path: frpc 可执行文件路径
            config_path: 配置文件路径
            
        Returns:
            启动脚本内容
        """
        script = f"""#!/bin/bash

# frpc 启动脚本

FRPC_PATH="{frpc_path}"
CONFIG_PATH="{config_path}"
PID_FILE="./frpc.pid"
LOG_FILE="./frpc.log"

start() {{
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "frpc 已经在运行中 (PID: $PID)"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "启动 frpc..."
    nohup "$FRPC_PATH" -c "$CONFIG_PATH" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "frpc 已启动 (PID: $(cat $PID_FILE))"
}}

stop() {{
    if [ ! -f "$PID_FILE" ]; then
        echo "frpc 未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "停止 frpc (PID: $PID)..."
        kill "$PID"
        rm -f "$PID_FILE"
        echo "frpc 已停止"
    else
        echo "frpc 进程不存在"
        rm -f "$PID_FILE"
    fi
}}

status() {{
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "frpc 正在运行 (PID: $PID)"
            return 0
        else
            echo "frpc 未运行（但 PID 文件存在）"
            return 1
        fi
    else
        echo "frpc 未运行"
        return 1
    fi
}}

restart() {{
    stop
    sleep 2
    start
}}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "用法: $0 {{start|stop|restart|status}}"
        exit 1
        ;;
esac

exit 0
"""
        return script
    
    def generate_startup_script_windows(
        self,
        frpc_path: str = "frpc.exe",
        config_path: str = "frpc.toml"
    ) -> str:
        """生成 Windows 启动脚本
        
        Args:
            frpc_path: frpc 可执行文件路径
            config_path: 配置文件路径
            
        Returns:
            启动脚本内容（PowerShell）
        """
        script = f"""# frpc 启动脚本 (PowerShell)

$FrpcPath = "{frpc_path}"
$ConfigPath = "{config_path}"
$LogFile = "frpc.log"

function Start-Frpc {{
    $processes = Get-Process -Name frpc -ErrorAction SilentlyContinue
    if ($processes) {{
        Write-Host "frpc 已经在运行中 (PID: $($processes.Id))"
        return
    }}
    
    Write-Host "启动 frpc..."
    Start-Process -FilePath $FrpcPath -ArgumentList "-c", $ConfigPath -RedirectStandardOutput $LogFile -WindowStyle Hidden
    Write-Host "frpc 已启动"
}}

function Stop-Frpc {{
    $processes = Get-Process -Name frpc -ErrorAction SilentlyContinue
    if (-not $processes) {{
        Write-Host "frpc 未运行"
        return
    }}
    
    Write-Host "停止 frpc (PID: $($processes.Id))..."
    Stop-Process -Name frpc -Force
    Write-Host "frpc 已停止"
}}

function Get-FrpcStatus {{
    $processes = Get-Process -Name frpc -ErrorAction SilentlyContinue
    if ($processes) {{
        Write-Host "frpc 正在运行 (PID: $($processes.Id))"
    }} else {{
        Write-Host "frpc 未运行"
    }}
}}

# 主逻辑
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

switch ($Action) {{
    "start" {{
        Start-Frpc
    }}
    "stop" {{
        Stop-Frpc
    }}
    "restart" {{
        Stop-Frpc
        Start-Sleep -Seconds 2
        Start-Frpc
    }}
    "status" {{
        Get-FrpcStatus
    }}
}}
"""
        return script
    
    def generate_systemd_service(
        self,
        frpc_path: str = "/usr/local/bin/frpc",
        config_path: str = "/etc/frp/frpc.toml",
        user: str = "nobody"
    ) -> str:
        """生成 systemd 服务文件
        
        Args:
            frpc_path: frpc 可执行文件路径
            config_path: 配置文件路径
            user: 运行用户
            
        Returns:
            systemd 服务文件内容
        """
        service = f"""[Unit]
Description=frp client service
After=network.target

[Service]
Type=simple
User={user}
Restart=on-failure
RestartSec=5s
ExecStart={frpc_path} -c {config_path}
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
"""
        return service

