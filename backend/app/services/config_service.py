"""配置生成服务"""
from typing import List, Optional
import toml
from sqlalchemy.orm import Session

from app.models.frps_server import FrpsServer
from app.schemas.config import ProxyConfig
from app.script_templates import load_shell_template


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
        return (
            load_shell_template("frpc_startup_linux.sh")
            .replace("@@FRPC_PATH@@", frpc_path)
            .replace("@@CONFIG_PATH@@", config_path)
        )
    
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
        return (
            load_shell_template("frpc_startup_windows.ps1")
            .replace("@@FRPC_PATH@@", frpc_path)
            .replace("@@CONFIG_PATH@@", config_path)
        )
    
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
        return (
            load_shell_template("frpc.service.unit")
            .replace("@@FRPC_PATH@@", frpc_path)
            .replace("@@CONFIG_PATH@@", config_path)
            .replace("@@SERVICE_USER@@", user)
        )

