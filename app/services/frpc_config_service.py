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
        client_name: str = None,
        format: str = "ini"
    ) -> str:
        """根据分组生成 frpc 配置文件
        
        Args:
            group_name: 分组名称
            frps_server_id: frps 服务器 ID
            client_name: 客户端名称（可选，默认使用分组名称）
            format: 配置格式，支持 'ini' 或 'toml'
            
        Returns:
            frpc 配置文件内容
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
        
        # 根据格式生成配置
        if format.lower() == "toml":
            return self._generate_toml_config(server, proxies, group_name, client_name)
        else:
            return self._generate_ini_config(server, proxies, group_name, client_name)
    
    def generate_config_for_proxies(
        self,
        proxy_ids: List[int],
        format: str = "ini"
    ) -> str:
        """根据代理ID列表生成 frpc 配置文件
        
        Args:
            proxy_ids: 代理ID列表
            format: 配置格式，支持 'ini' 或 'toml'
            
        Returns:
            frpc 配置文件内容
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
        
        # 根据格式生成配置
        group_name = proxies[0].group_name if proxies else "selected"
        if format.lower() == "toml":
            return self._generate_toml_config(server, proxies, group_name, None)
        else:
            return self._generate_ini_config(server, proxies, group_name, None)
    
    def _generate_ini_config(self, server: FrpsServer, proxies: List[Proxy], group_name: str, client_name: str = None) -> str:
        """生成 INI 格式的配置文件
        
        Args:
            server: 服务器对象
            proxies: 代理列表
            group_name: 分组名称
            client_name: 客户端名称（可选）
            
        Returns:
            INI 格式配置内容
        """
        config_lines = []
        
        # 注释头部
        config_lines.append("# frpc 配置文件 (INI 格式)")
        config_lines.append(f"# 分组: {group_name}")
        config_lines.append(f"# 服务器: {server.name}")
        config_lines.append(f"# 代理数量: {len(proxies)}")
        config_lines.append(f"# 生成时间: {self._get_current_time()}")
        config_lines.append("")
        
        # [common] 部分
        config_lines.append("[common]")
        config_lines.append(f"server_addr = {server.server_addr}")
        config_lines.append(f"server_port = {server.server_port}")
        
        # 认证配置 - 优先使用 auth_token
        if server.auth_token:
            config_lines.append(f"auth_token = {server.auth_token}")
        elif server.auth_username and server.auth_password:
            config_lines.append(f"# 使用用户名密码认证")
            config_lines.append(f"user = {server.auth_username}")
            config_lines.append(f"# 注意：新版本 frp 推荐使用 token 认证")
        
        config_lines.append("")
        
        # 生成每个代理的配置
        for proxy in proxies:
            config_lines.append(f"[{proxy.name}]")
            config_lines.append(f"type = {proxy.proxy_type}")
            config_lines.append(f"local_ip = {proxy.local_ip}")
            config_lines.append(f"local_port = {proxy.local_port}")
            
            # TCP/UDP 类型需要指定远程端口
            if proxy.proxy_type in ["tcp", "udp"] and proxy.remote_port:
                config_lines.append(f"remote_port = {proxy.remote_port}")
            
            # HTTP/HTTPS 类型可能需要自定义域名
            if proxy.proxy_type in ["http", "https"]:
                config_lines.append(f"# custom_domains = example.com")
            
            config_lines.append("")
        
        return "\n".join(config_lines)
    
    def _generate_toml_config(self, server: FrpsServer, proxies: List[Proxy], group_name: str, client_name: str = None) -> str:
        """生成 TOML 格式的配置文件
        
        Args:
            server: 服务器对象
            proxies: 代理列表
            group_name: 分组名称
            client_name: 客户端名称（可选）
            
        Returns:
            TOML 格式配置内容
        """
        config_lines = []
        
        # 注释头部
        config_lines.append("# frpc 配置文件 (TOML 格式)")
        config_lines.append(f"# 分组: {group_name}")
        config_lines.append(f"# 服务器: {server.name}")
        config_lines.append(f"# 代理数量: {len(proxies)}")
        config_lines.append(f"# 生成时间: {self._get_current_time()}")
        config_lines.append("")
        
        # 服务器配置部分
        config_lines.append(f"serverAddr = \"{server.server_addr}\"")
        config_lines.append(f"serverPort = {server.server_port}")
        
        # 认证配置 - 优先使用 auth_token
        if server.auth_token:
            config_lines.append(f"auth.token = \"{server.auth_token}\"")
        elif server.auth_username and server.auth_password:
            config_lines.append(f"# 使用用户名密码认证（新版本推荐使用 token）")
            config_lines.append(f"# auth.method = \"token\"")
        
        config_lines.append("")
        
        # 生成每个代理的配置
        for proxy in proxies:
            config_lines.append(f"[[proxies]]")
            config_lines.append(f"name = \"{proxy.name}\"")
            config_lines.append(f"type = \"{proxy.proxy_type}\"")
            config_lines.append(f"localIP = \"{proxy.local_ip}\"")
            config_lines.append(f"localPort = {proxy.local_port}")
            
            # TCP/UDP 类型需要指定远程端口
            if proxy.proxy_type in ["tcp", "udp"] and proxy.remote_port:
                config_lines.append(f"remotePort = {proxy.remote_port}")
            
            # HTTP/HTTPS 类型可能需要自定义域名
            if proxy.proxy_type in ["http", "https"]:
                config_lines.append(f"# customDomains = [\"example.com\"]")
            
            config_lines.append("")
        
        return "\n".join(config_lines)
    
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

    def get_install_script_with_auth(
        self,
        group_name: str,
        frps_server_id: int,
        install_path: str = "/opt/frp",
        api_base_url: str = "",
        auth_username: str = "",
        auth_password: str = "",
        server_name: str = ""
    ) -> str:
        """生成带认证URL的 frpc 安装脚本
        
        此脚本会从 API 下载配置文件，而不是嵌入配置内容。
        
        Args:
            group_name: 分组名称
            frps_server_id: frps 服务器 ID
            install_path: 安装路径
            api_base_url: API 基础 URL
            auth_username: 认证用户名
            auth_password: 认证密码
            server_name: 服务器名称
            
        Returns:
            安装脚本内容（Shell 脚本）
        """
        # 构建配置下载 URL - 使用新的URL格式
        # 格式: /api/frpc/config/direct/{server_name}/{group_name}/frpc.ini
        # 生成 token (base64编码的 username:password)
        import base64
        token = base64.b64encode(f"{auth_username}:{auth_password}".encode()).decode()
        config_url = f"{api_base_url}/api/frpc/config/direct/{server_name}/{group_name}/frpc.ini?token={token}"
        
        script_lines = [
            "#!/bin/bash",
            "# frpc 自动安装脚本（远程配置版）",
            f"# 分组: {group_name}",
            f"# API: {api_base_url}",
            "",
            "set -e",
            "",
            f"INSTALL_PATH=\"{install_path}\"",
            f"CONFIG_FILE=\"$INSTALL_PATH/frpc.ini\"",
            f"SERVICE_NAME=\"frpc\"",
            f"CONFIG_URL=\"{config_url}\"",
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
            "# 从 API 下载配置文件",
            'echo "从服务器下载配置文件..."',
            'curl -f "$CONFIG_URL" -o "$CONFIG_FILE"',
            'if [ $? -ne 0 ]; then',
            '    echo "配置文件下载失败！请检查访问令牌和网络连接。"',
            '    exit 1',
            'fi',
            'echo "配置文件下载成功: $CONFIG_FILE"',
            "",
            "# 下载 frpc（如果不存在）",
            'if [ ! -f "$INSTALL_PATH/frpc" ]; then',
            '    echo "下载 frpc..."',
            '    # 根据系统架构下载对应的 frpc',
            '    ARCH=$(uname -m)',
            '    if [ "$ARCH" = "x86_64" ]; then',
            '        FRPC_URL="https://github.com/fatedier/frp/releases/download/v0.52.0/frp_0.52.0_linux_amd64.tar.gz"',
            '    elif [ "$ARCH" = "aarch64" ]; then',
            '        FRPC_URL="https://github.com/fatedier/frp/releases/download/v0.52.0/frp_0.52.0_linux_arm64.tar.gz"',
            '    else',
            '        echo "不支持的系统架构: $ARCH"',
            '        exit 1',
            '    fi',
            '    wget -O /tmp/frp.tar.gz "$FRPC_URL"',
            '    tar -xzf /tmp/frp.tar.gz -C /tmp',
            '    mv /tmp/frp_*/frpc "$INSTALL_PATH/"',
            '    chmod +x "$INSTALL_PATH/frpc"',
            '    rm -rf /tmp/frp*',
            '    echo "frpc 下载完成"',
            'else',
            '    echo "frpc 已存在，跳过下载"',
            'fi',
            "",
            "# 创建配置更新脚本",
            'cat > "$INSTALL_PATH/update_config.sh" << \"EOF_UPDATE\"',
            "#!/bin/bash",
            "# frpc 配置更新脚本",
            f"CONFIG_URL=\"{config_url}\"",
            f"CONFIG_FILE=\"{install_path}/frpc.ini\"",
            "",
            'echo "正在更新配置..."',
            'curl -f "$CONFIG_URL" -o "$CONFIG_FILE.new"',
            'if [ $? -eq 0 ]; then',
            '    mv "$CONFIG_FILE.new" "$CONFIG_FILE"',
            '    echo "配置更新成功"',
            '    systemctl restart frpc',
            '    echo "frpc 服务已重启"',
            'else',
            '    echo "配置更新失败！请检查访问令牌和网络连接。"',
            '    rm -f "$CONFIG_FILE.new"',
            '    exit 1',
            'fi',
            "EOF_UPDATE",
            'chmod +x "$INSTALL_PATH/update_config.sh"',
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
            'systemctl restart "$SERVICE_NAME"',
            "",
            'echo ""',
            'echo "============================================"',
            'echo "安装完成！"',
            'echo "============================================"',
            'echo "服务名称: $SERVICE_NAME"',
            'echo "配置文件: $CONFIG_FILE"',
            'echo "安装路径: $INSTALL_PATH"',
            'echo ""',
            'echo "常用命令："',
            'echo "  查看状态: systemctl status $SERVICE_NAME"',
            'echo "  查看日志: journalctl -u $SERVICE_NAME -f"',
            'echo "  重启服务: systemctl restart $SERVICE_NAME"',
            'echo "  停止服务: systemctl stop $SERVICE_NAME"',
            'echo "  更新配置: $INSTALL_PATH/update_config.sh"',
            'echo ""',
            'echo "配置 URL: $CONFIG_URL"',
            'echo "============================================"',
        ]
        
        return "\n".join(script_lines)

