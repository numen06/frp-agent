"""frpc 配置生成服务"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.proxy import Proxy
from app.models.frps_server import FrpsServer


class FrpcConfigService:
    """frpc 配置生成服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_config_for_group(
        self,
        group_name: str,
        frps_server_id: int,
        client_name: str = None
    ) -> str:
        """根据分组生成 frpc 配置文件
        
        Args:
            group_name: 分组名称
            frps_server_id: frps 服务器 ID
            client_name: 客户端名称（可选，默认使用分组名称）
            
        Returns:
            frpc 配置文件内容（TOML 格式）
        """
        # 获取服务器配置
        server = self.db.query(FrpsServer).filter(
            FrpsServer.id == frps_server_id
        ).first()
        
        if not server:
            raise ValueError(f"服务器 ID {frps_server_id} 不存在")
        
        # 获取该分组的所有代理
        proxies = self.db.query(Proxy).filter(
            Proxy.group_name == group_name,
            Proxy.frps_server_id == frps_server_id
        ).all()
        
        if not proxies:
            raise ValueError(f"分组 '{group_name}' 在服务器 {server.name} 中没有代理")
        
        # 使用分组名称作为客户端名称
        if not client_name:
            client_name = group_name
        
        # 生成配置
        config_lines = []
        
        # 服务器配置部分
        config_lines.append("# frpc 配置文件")
        config_lines.append(f"# 分组: {group_name}")
        config_lines.append(f"# 服务器: {server.name}")
        config_lines.append(f"# 生成时间: {self._get_current_time()}")
        config_lines.append("")
        config_lines.append("[common]")
        
        # 解析服务器地址和端口
        server_addr, server_port = self._parse_server_address(server.api_base_url)
        config_lines.append(f"server_addr = {server_addr}")
        config_lines.append(f"server_port = {server_port}")
        
        # 如果需要认证
        if server.auth_username and server.auth_password:
            config_lines.append(f"auth_token = {server.auth_password}")
        
        config_lines.append("")
        
        # 生成每个代理的配置
        for proxy in proxies:
            config_lines.extend(self._generate_proxy_section(proxy))
            config_lines.append("")
        
        return "\n".join(config_lines)
    
    def generate_config_for_proxies(
        self,
        proxy_ids: List[int]
    ) -> str:
        """根据代理ID列表生成 frpc 配置文件
        
        Args:
            proxy_ids: 代理ID列表
            
        Returns:
            frpc 配置文件内容（TOML 格式）
        """
        # 获取代理
        proxies = self.db.query(Proxy).filter(Proxy.id.in_(proxy_ids)).all()
        
        if not proxies:
            raise ValueError("未找到指定的代理")
        
        # 检查所有代理是否在同一服务器
        server_ids = set([p.frps_server_id for p in proxies])
        if len(server_ids) > 1:
            raise ValueError("代理必须在同一个服务器上")
        
        # 获取服务器配置
        server = self.db.query(FrpsServer).filter(
            FrpsServer.id == list(server_ids)[0]
        ).first()
        
        if not server:
            raise ValueError("服务器不存在")
        
        # 生成配置
        config_lines = []
        
        # 服务器配置部分
        config_lines.append("# frpc 配置文件")
        config_lines.append(f"# 服务器: {server.name}")
        config_lines.append(f"# 代理数量: {len(proxies)}")
        config_lines.append(f"# 生成时间: {self._get_current_time()}")
        config_lines.append("")
        config_lines.append("[common]")
        
        # 解析服务器地址和端口
        server_addr, server_port = self._parse_server_address(server.api_base_url)
        config_lines.append(f"server_addr = {server_addr}")
        config_lines.append(f"server_port = {server_port}")
        
        # 如果需要认证
        if server.auth_username and server.auth_password:
            config_lines.append(f"auth_token = {server.auth_password}")
        
        config_lines.append("")
        
        # 生成每个代理的配置
        for proxy in proxies:
            config_lines.extend(self._generate_proxy_section(proxy))
            config_lines.append("")
        
        return "\n".join(config_lines)
    
    def _generate_proxy_section(self, proxy: Proxy) -> List[str]:
        """生成单个代理的配置段
        
        Args:
            proxy: 代理对象
            
        Returns:
            配置行列表
        """
        lines = []
        lines.append(f"[{proxy.name}]")
        lines.append(f"type = {proxy.proxy_type}")
        lines.append(f"local_ip = {proxy.local_ip}")
        lines.append(f"local_port = {proxy.local_port}")
        
        # TCP/UDP 类型需要指定远程端口
        if proxy.proxy_type in ["tcp", "udp"] and proxy.remote_port:
            lines.append(f"remote_port = {proxy.remote_port}")
        
        # HTTP/HTTPS 类型可能需要自定义域名
        if proxy.proxy_type in ["http", "https"]:
            lines.append(f"# custom_domains = example.com")
        
        return lines
    
    def _parse_server_address(self, api_base_url: str) -> tuple:
        """从 API URL 解析服务器地址和端口
        
        Args:
            api_base_url: API 基础 URL，如 http://example.com:7000
            
        Returns:
            (server_addr, server_port) 元组
        """
        # 去除协议部分
        url = api_base_url.replace("http://", "").replace("https://", "")
        
        # 去除路径部分
        if "/" in url:
            url = url.split("/")[0]
        
        # 解析地址和端口
        if ":" in url:
            addr, port = url.rsplit(":", 1)
            return addr, port
        else:
            # 默认端口 7000
            return url, "7000"
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_install_script(
        self,
        group_name: str,
        frps_server_id: int,
        install_path: str = "/etc/frp"
    ) -> str:
        """生成 frpc 安装脚本
        
        Args:
            group_name: 分组名称
            frps_server_id: frps 服务器 ID
            install_path: 安装路径
            
        Returns:
            安装脚本内容（Shell 脚本）
        """
        config_content = self.generate_config_for_group(group_name, frps_server_id)
        
        script_lines = [
            "#!/bin/bash",
            "# frpc 自动安装脚本",
            f"# 分组: {group_name}",
            "",
            "set -e",
            "",
            f"INSTALL_PATH=\"{install_path}\"",
            f"CONFIG_FILE=\"$INSTALL_PATH/frpc_{group_name}.ini\"",
            f"SERVICE_NAME=\"frpc_{group_name}\"",
            "",
            "# 检查是否为 root 用户",
            'if [ "$EUID" -ne 0 ]; then',
            '    echo "请使用 root 权限运行此脚本"',
            '    exit 1',
            'fi',
            "",
            "# 创建安装目录",
            'echo "创建安装目录: $INSTALL_PATH"',
            'mkdir -p "$INSTALL_PATH"',
            "",
            "# 写入配置文件",
            'echo "生成配置文件: $CONFIG_FILE"',
            'cat > "$CONFIG_FILE" << EOF',
            config_content,
            'EOF',
            "",
            "# 下载 frpc（如果不存在）",
            'if [ ! -f "$INSTALL_PATH/frpc" ]; then',
            '    echo "下载 frpc..."',
            '    # 根据系统架构下载对应的 frpc',
            '    ARCH=$(uname -m)',
            '    if [ "$ARCH" = "x86_64" ]; then',
            '        wget -O /tmp/frp.tar.gz https://github.com/fatedier/frp/releases/download/v0.52.0/frp_0.52.0_linux_amd64.tar.gz',
            '    elif [ "$ARCH" = "aarch64" ]; then',
            '        wget -O /tmp/frp.tar.gz https://github.com/fatedier/frp/releases/download/v0.52.0/frp_0.52.0_linux_arm64.tar.gz',
            '    fi',
            '    tar -xzf /tmp/frp.tar.gz -C /tmp',
            '    mv /tmp/frp_*/frpc "$INSTALL_PATH/"',
            '    chmod +x "$INSTALL_PATH/frpc"',
            '    rm -rf /tmp/frp*',
            'fi',
            "",
            "# 创建 systemd 服务",
            'echo "创建 systemd 服务: $SERVICE_NAME"',
            'cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF',
            "[Unit]",
            f"Description=frpc service for {group_name}",
            "After=network.target",
            "",
            "[Service]",
            "Type=simple",
            'ExecStart=$INSTALL_PATH/frpc -c $CONFIG_FILE',
            "Restart=on-failure",
            "RestartSec=5s",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "EOF",
            "",
            "# 重载 systemd 并启动服务",
            "systemctl daemon-reload",
            'systemctl enable "$SERVICE_NAME"',
            'systemctl start "$SERVICE_NAME"',
            "",
            'echo "安装完成！"',
            'echo "服务名称: $SERVICE_NAME"',
            'echo "配置文件: $CONFIG_FILE"',
            'echo "查看状态: systemctl status $SERVICE_NAME"',
            'echo "查看日志: journalctl -u $SERVICE_NAME -f"',
        ]
        
        return "\n".join(script_lines)

