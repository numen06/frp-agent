"""frps API 客户端"""
import httpx
from typing import List, Dict, Optional
from app.models.frps_server import FrpsServer


class FrpsClient:
    """frps API 客户端"""
    
    def __init__(self, server: FrpsServer):
        """初始化客户端
        
        Args:
            server: frps 服务器配置
        """
        self.server = server
        self.base_url = server.api_base_url.rstrip("/")
        self.auth = (server.auth_username, server.auth_password)
    
    async def get_tcp_proxies(self) -> List[Dict]:
        """获取 TCP 代理列表
        
        Returns:
            代理列表
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/proxy/tcp",
                    auth=self.auth
                )
                response.raise_for_status()
                data = response.json()
                return data.get("proxies", [])
        except Exception as e:
            print(f"获取 TCP 代理失败: {e}")
            return []
    
    async def get_udp_proxies(self) -> List[Dict]:
        """获取 UDP 代理列表
        
        Returns:
            代理列表
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/proxy/udp",
                    auth=self.auth
                )
                response.raise_for_status()
                data = response.json()
                return data.get("proxies", [])
        except Exception as e:
            print(f"获取 UDP 代理失败: {e}")
            return []
    
    async def get_http_proxies(self) -> List[Dict]:
        """获取 HTTP 代理列表
        
        Returns:
            代理列表
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/proxy/http",
                    auth=self.auth
                )
                response.raise_for_status()
                data = response.json()
                return data.get("proxies", [])
        except Exception as e:
            print(f"获取 HTTP 代理失败: {e}")
            return []
    
    async def get_https_proxies(self) -> List[Dict]:
        """获取 HTTPS 代理列表
        
        Returns:
            代理列表
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/proxy/https",
                    auth=self.auth
                )
                response.raise_for_status()
                data = response.json()
                return data.get("proxies", [])
        except Exception as e:
            print(f"获取 HTTPS 代理失败: {e}")
            return []
    
    async def get_all_proxies(self) -> Dict[str, List[Dict]]:
        """获取所有类型的代理
        
        Returns:
            按类型分组的代理字典
        """
        tcp_proxies = await self.get_tcp_proxies()
        udp_proxies = await self.get_udp_proxies()
        http_proxies = await self.get_http_proxies()
        https_proxies = await self.get_https_proxies()
        
        return {
            "tcp": tcp_proxies,
            "udp": udp_proxies,
            "http": http_proxies,
            "https": https_proxies,
        }
    
    async def get_proxy_by_name(self, name: str, proxy_type: str = "tcp") -> Optional[Dict]:
        """根据名称获取代理信息
        
        Args:
            name: 代理名称
            proxy_type: 代理类型
            
        Returns:
            代理信息，如果不存在返回 None
        """
        proxies = []
        if proxy_type == "tcp":
            proxies = await self.get_tcp_proxies()
        elif proxy_type == "udp":
            proxies = await self.get_udp_proxies()
        elif proxy_type == "http":
            proxies = await self.get_http_proxies()
        elif proxy_type == "https":
            proxies = await self.get_https_proxies()
        
        for proxy in proxies:
            if proxy.get("name") == name:
                return proxy
        
        return None
    
    def parse_proxy_info(self, proxy_data: Dict) -> Dict:
        """解析代理信息
        
        Args:
            proxy_data: 原始代理数据
            
        Returns:
            解析后的代理信息
        """
        conf = proxy_data.get("conf", {})
        return {
            "name": proxy_data.get("name"),
            "status": proxy_data.get("status", "offline"),
            "proxy_type": conf.get("type", "tcp") if conf else "tcp",
            "remote_port": conf.get("remotePort") if conf else None,
            "local_ip": conf.get("localIP", "127.0.0.1") if conf else "127.0.0.1",
            "client_version": proxy_data.get("clientVersion"),
            "today_traffic_in": proxy_data.get("todayTrafficIn", 0),
            "today_traffic_out": proxy_data.get("todayTrafficOut", 0),
            "cur_conns": proxy_data.get("curConns", 0),
            "last_start_time": proxy_data.get("lastStartTime"),
            "last_close_time": proxy_data.get("lastCloseTime"),
        }

