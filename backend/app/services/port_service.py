"""端口管理服务"""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models.port import PortAllocation
from app.models.proxy import Proxy
from app.models.history import ProxyHistory


class PortService:
    """端口管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def allocate_port(
        self,
        frps_server_id: int,
        port: int,
        allocated_to: str
    ) -> PortAllocation:
        """分配端口
        
        Args:
            frps_server_id: frps 服务器 ID
            port: 端口号
            allocated_to: 分配给哪个代理
            
        Returns:
            端口分配记录
        """
        # 检查端口是否已分配
        existing = self.db.query(PortAllocation).filter(
            PortAllocation.frps_server_id == frps_server_id,
            PortAllocation.port == port,
            PortAllocation.is_allocated == True
        ).first()
        
        if existing:
            raise ValueError(f"端口 {port} 已被分配给 {existing.allocated_to}")
        
        # 创建新的分配记录
        allocation = PortAllocation(
            frps_server_id=frps_server_id,
            port=port,
            is_allocated=True,
            allocated_to=allocated_to,
            allocated_at=datetime.utcnow()
        )
        
        self.db.add(allocation)
        
        # 记录历史
        history = ProxyHistory(
            frps_server_id=frps_server_id,
            proxy_name=allocated_to,
            action="port_allocated",
            timestamp=datetime.utcnow(),
            details=json.dumps({"port": port})
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(allocation)
        
        return allocation
    
    def release_port(
        self,
        frps_server_id: int,
        port: int
    ) -> bool:
        """释放端口
        
        Args:
            frps_server_id: frps 服务器 ID
            port: 端口号
            
        Returns:
            是否成功释放
        """
        allocation = self.db.query(PortAllocation).filter(
            PortAllocation.frps_server_id == frps_server_id,
            PortAllocation.port == port,
            PortAllocation.is_allocated == True
        ).first()
        
        if not allocation:
            return False
        
        allocated_to = allocation.allocated_to
        
        # 标记为未分配
        allocation.is_allocated = False
        
        # 记录历史
        history = ProxyHistory(
            frps_server_id=frps_server_id,
            proxy_name=allocated_to or "unknown",
            action="port_released",
            timestamp=datetime.utcnow(),
            details=json.dumps({"port": port})
        )
        self.db.add(history)
        
        self.db.commit()
        
        return True
    
    def is_port_available(
        self,
        frps_server_id: int,
        port: int
    ) -> bool:
        """检查端口是否可用
        
        会同时检查PortAllocation表和Proxy表中的端口使用情况。
        
        Args:
            frps_server_id: frps 服务器 ID
            port: 端口号
            
        Returns:
            端口是否可用
        """
        # 检查PortAllocation表中是否已分配
        allocation = self.db.query(PortAllocation).filter(
            PortAllocation.frps_server_id == frps_server_id,
            PortAllocation.port == port,
            PortAllocation.is_allocated == True
        ).first()
        
        if allocation:
            return False
        
        # 检查Proxy表中是否有代理使用该端口
        proxy = self.db.query(Proxy).filter(
            Proxy.frps_server_id == frps_server_id,
            Proxy.remote_port == port
        ).first()
        
        return proxy is None
    
    def get_allocated_ports(
        self,
        frps_server_id: int
    ) -> List[PortAllocation]:
        """获取已分配的端口列表
        
        Args:
            frps_server_id: frps 服务器 ID
            
        Returns:
            已分配的端口列表
        """
        return self.db.query(PortAllocation).filter(
            PortAllocation.frps_server_id == frps_server_id,
            PortAllocation.is_allocated == True
        ).all()
    
    def detect_conflicts(
        self,
        frps_server_id: int,
        active_proxies: List[dict]
    ) -> List[dict]:
        """检测端口冲突
        
        Args:
            frps_server_id: frps 服务器 ID
            active_proxies: 从 frps API 获取的活跃代理列表
            
        Returns:
            冲突列表
        """
        conflicts = []
        
        # 获取数据库中的代理记录
        db_proxies = self.db.query(Proxy).filter(
            Proxy.frps_server_id == frps_server_id,
            Proxy.remote_port.isnot(None)
        ).all()
        
        # 构建端口到代理的映射
        port_map = {}
        for proxy_data in active_proxies:
            conf = proxy_data.get("conf")
            if conf:
                remote_port = conf.get("remotePort")
                if remote_port:
                    if remote_port not in port_map:
                        port_map[remote_port] = []
                    port_map[remote_port].append(proxy_data.get("name"))
        
        # 检测同一端口被多个代理使用
        for port, proxy_names in port_map.items():
            if len(proxy_names) > 1:
                conflicts.append({
                    "port": port,
                    "conflict_type": "multiple_proxies",
                    "proxies": proxy_names,
                    "message": f"端口 {port} 被多个代理使用: {', '.join(proxy_names)}"
                })
        
        # 检测数据库记录与实际运行不一致
        for db_proxy in db_proxies:
            if db_proxy.status == "online":
                # 检查是否真的在线
                found = False
                for proxy_data in active_proxies:
                    if (proxy_data.get("name") == db_proxy.name and
                        proxy_data.get("status") == "online"):
                        found = True
                        break
                
                if not found:
                    conflicts.append({
                        "port": db_proxy.remote_port,
                        "conflict_type": "status_mismatch",
                        "proxy_name": db_proxy.name,
                        "message": f"代理 {db_proxy.name} 数据库显示在线但实际已下线"
                    })
        
        return conflicts
    
    def get_next_available_port(
        self,
        frps_server_id: int,
        start_port: int = 6000,
        end_port: int = 7000
    ) -> Optional[int]:
        """获取下一个可用端口
        
        优先从已分配的最大端口号+1开始查找，如果没有已分配的端口则从start_port开始。
        这样可以保证端口号连续递增。
        
        会同时查询PortAllocation表和Proxy表中的端口使用情况，确保找到真正的最大端口号。
        
        Args:
            frps_server_id: frps 服务器 ID
            start_port: 起始端口（默认6000）
            end_port: 结束端口（默认7000）
            
        Returns:
            可用端口号，如果没有可用端口返回 None
        """
        # 获取PortAllocation表中已分配的端口
        allocated_ports = set(
            alloc.port for alloc in self.get_allocated_ports(frps_server_id)
        )
        
        # 获取Proxy表中所有代理使用的remote_port
        proxy_ports = self.db.query(Proxy.remote_port).filter(
            Proxy.frps_server_id == frps_server_id,
            Proxy.remote_port.isnot(None)
        ).all()
        
        # 将Proxy表中的端口也加入已使用端口集合
        for (port,) in proxy_ports:
            if port is not None:
                allocated_ports.add(port)
        
        # 如果没有已使用的端口，从start_port开始
        if not allocated_ports:
            # 确保start_port在范围内
            if start_port <= end_port:
                return start_port
            return None
        
        # 找到已使用的最大端口号
        max_used_port = max(allocated_ports)
        
        # 从最大端口号+1开始查找（但不能小于start_port）
        search_start = max(max_used_port + 1, start_port)
        
        # 从最大端口号+1开始往后查找
        for port in range(search_start, end_port + 1):
            if port not in allocated_ports:
                return port
        
        # 如果从最大端口号+1开始找不到，再从start_port开始查找（处理中间有空隙的情况）
        # 但只查找小于最大端口号的端口
        if max_used_port > start_port:
            for port in range(start_port, max_used_port):
                if port not in allocated_ports:
                    return port
        
        return None

