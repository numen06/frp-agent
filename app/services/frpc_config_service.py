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
    
    def convert_ini_to_toml(self, ini_content: str) -> str:
        """将INI格式的frpc配置转换为TOML格式
        
        Args:
            ini_content: INI格式的配置内容
            
        Returns:
            TOML格式的配置内容
        """
        import configparser
        from io import StringIO
        
        try:
            # 解析INI配置
            config = configparser.ConfigParser()
            config.read_string(ini_content)
            
            toml_lines = []
            toml_lines.append("# frpc 配置文件 (TOML 格式)")
            toml_lines.append("# 由 INI 格式自动转换")
            toml_lines.append(f"# 转换时间: {self._get_current_time()}")
            toml_lines.append("")
            
            # 处理 [common] 部分
            if 'common' in config:
                common = config['common']
                
                # 服务器地址和端口
                if 'server_addr' in common:
                    toml_lines.append(f"serverAddr = \"{common['server_addr']}\"")
                if 'server_port' in common:
                    toml_lines.append(f"serverPort = {common['server_port']}")
                
                # 认证
                if 'auth_token' in common or 'token' in common:
                    token = common.get('auth_token') or common.get('token')
                    toml_lines.append(f"auth.token = \"{token}\"")
                elif 'user' in common:
                    toml_lines.append(f"# 原配置使用用户名认证，新版本推荐使用 token")
                    toml_lines.append(f"# auth.method = \"token\"")
                
                # 其他常见配置
                if 'login_fail_exit' in common:
                    toml_lines.append(f"loginFailExit = {common['login_fail_exit'].lower()}")
                if 'protocol' in common:
                    toml_lines.append(f"transport.protocol = \"{common['protocol']}\"")
                if 'tls_enable' in common:
                    toml_lines.append(f"transport.tls.enable = {common['tls_enable'].lower()}")
                
                toml_lines.append("")
            
            # 处理代理配置
            for section in config.sections():
                if section == 'common':
                    continue
                
                proxy = config[section]
                toml_lines.append("[[proxies]]")
                toml_lines.append(f"name = \"{section}\"")
                
                # 代理类型
                if 'type' in proxy:
                    toml_lines.append(f"type = \"{proxy['type']}\"")
                
                # 本地配置
                if 'local_ip' in proxy:
                    toml_lines.append(f"localIP = \"{proxy['local_ip']}\"")
                if 'local_port' in proxy:
                    toml_lines.append(f"localPort = {proxy['local_port']}")
                
                # 远程端口
                if 'remote_port' in proxy:
                    toml_lines.append(f"remotePort = {proxy['remote_port']}")
                
                # HTTP/HTTPS 特有配置
                if 'custom_domains' in proxy:
                    domains = proxy['custom_domains'].split(',')
                    domains_str = ', '.join([f'\"{d.strip()}\"' for d in domains])
                    toml_lines.append(f"customDomains = [{domains_str}]")
                
                if 'subdomain' in proxy:
                    toml_lines.append(f"subdomain = \"{proxy['subdomain']}\"")
                
                # 其他配置
                if 'use_encryption' in proxy:
                    toml_lines.append(f"transport.useEncryption = {proxy['use_encryption'].lower()}")
                if 'use_compression' in proxy:
                    toml_lines.append(f"transport.useCompression = {proxy['use_compression'].lower()}")
                
                toml_lines.append("")
            
            return "\n".join(toml_lines)
            
        except Exception as e:
            raise ValueError(f"INI 转换失败: {str(e)}")
