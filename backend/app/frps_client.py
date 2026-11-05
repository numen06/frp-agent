"""frps API 客户端"""
import asyncio
import httpx
from typing import List, Dict, Optional
from app.models.frps_server import FrpsServer

PROXY_TYPES = ('tcp', 'udp', 'http', 'https', 'stcp', 'sudp', 'xtcp', 'tcpmux')


class FrpsCollectionError(RuntimeError):
    """A failed collection is never an empty successful snapshot."""


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
    
    async def _get_proxies(self, proxy_type, client, optional=False):
        try:
            response = await client.get(f"{self.base_url}/proxy/{proxy_type}", auth=self.auth)
            if optional and response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or 'proxies' not in data:
                raise ValueError('invalid snapshot')
            rows = data['proxies']
            if rows is None:
                rows = []
            if not isinstance(rows, list) or any(
                not isinstance(row, dict) or not isinstance(row.get('name'), str)
                or not row['name'] or row.get('status') not in {'online', 'offline'}
                or (row.get('conf') is not None and not isinstance(row['conf'], dict))
                for row in rows
            ):
                raise ValueError('invalid proxy rows')
            return rows
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            reason = f"HTTP {exc.response.status_code}" if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
            raise FrpsCollectionError(f"{proxy_type.upper()} 状态采集失败（{reason}），保留上次状态") from exc

    async def _get_type(self, proxy_type):
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await self._get_proxies(proxy_type, client)

    async def get_tcp_proxies(self) -> List[Dict]:
        return await self._get_type('tcp')

    async def get_udp_proxies(self) -> List[Dict]:
        return await self._get_type('udp')

    async def get_http_proxies(self) -> List[Dict]:
        return await self._get_type('http')

    async def get_https_proxies(self) -> List[Dict]:
        return await self._get_type('https')

    async def get_server_info(self) -> Optional[Dict]:
        """获取 frps 服务端信息

        Returns:
            服务端信息字典，失败时返回 None
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/serverinfo",
                    auth=self.auth,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"获取 frps 服务端信息失败: {e}")
            return None

    async def get_server_version(self) -> Optional[str]:
        """获取 frps 服务端版本"""
        info = await self.get_server_info()
        if not info:
            return None
        for key in ("version", "server_version", "serverVersion"):
            value = info.get(key)
            if value:
                return str(value)
        return None

    async def get_all_proxies(self) -> Dict[str, List[Dict]]:
        # A single pool, bounded eight requests; apply only a complete successful snapshot.
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await asyncio.gather(*(
                self._get_proxies(kind, client, optional=kind not in PROXY_TYPES[:4])
                for kind in PROXY_TYPES
            ), return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                raise result
        return {kind: rows for kind, rows in zip(PROXY_TYPES, results) if rows is not None}

    async def get_proxy_by_name(self, name: str, proxy_type: str = "tcp") -> Optional[Dict]:
        if proxy_type not in PROXY_TYPES:
            return None
        return next((p for p in await self._get_type(proxy_type) if p['name'] == name), None)

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
            "today_traffic_in": proxy_data.get("todayTrafficIn"),
            "today_traffic_out": proxy_data.get("todayTrafficOut"),
            "cur_conns": proxy_data.get("curConns"),
            "last_start_time": proxy_data.get("lastStartTime"),
            "last_close_time": proxy_data.get("lastCloseTime"),
        }

