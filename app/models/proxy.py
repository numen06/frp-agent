"""代理记录模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Proxy(Base):
    """代理记录表"""
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True, index=True)
    frps_server_id = Column(Integer, ForeignKey("frps_servers.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    group_name = Column(String(50), nullable=True, index=True)  # 分组名称，从代理名称中解析
    proxy_type = Column(String(20), nullable=False, default="tcp")  # tcp, udp, http, https, stcp, xtcp
    remote_port = Column(Integer, nullable=True)  # TCP/UDP 代理的远程端口
    local_ip = Column(String(50), nullable=False, default="127.0.0.1")
    local_port = Column(Integer, nullable=False)
    client_name = Column(String(100), nullable=True)  # 客户端名称
    status = Column(String(20), default="offline")  # online, offline
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    frps_server = relationship("FrpsServer", back_populates="proxies")
    
    @staticmethod
    def parse_group_name(proxy_name: str) -> str:
        """从代理名称中解析分组名称
        
        例如: dlyy_rdp -> dlyy
        
        Args:
            proxy_name: 代理名称
            
        Returns:
            分组名称，如果没有下划线则返回"其他"
        """
        if "_" in proxy_name:
            group = proxy_name.split("_")[0]
            return group if group else "其他"
        return "其他"
    
    @staticmethod
    def auto_detect_local_port(proxy_name: str) -> int:
        """根据代理名称自动识别本地端口
        
        通过代理名称中的关键字识别常用服务的默认端口
        
        Args:
            proxy_name: 代理名称
            
        Returns:
            识别到的端口号，如果无法识别则返回 0
        """
        # 端口映射表（使用列表保持顺序，长关键字优先）
        port_mappings = [
            # 先检查长关键字和特殊关键字
            ('elasticsearch', 9200),
            ('postgresql', 5432),
            ('prometheus', 9090),
            ('minecraft', 25565),
            ('mariadb', 3306),
            ('mongodb', 27017),
            ('terraria', 7777),
            # HTTPS 必须在 HTTP 之前检查
            ('https', 443),
            # VNC 必须在 remote 之前检查，因为 vnc_remote 应该识别为 vnc
            ('vnc', 5900),
            # 远程桌面
            ('rdp', 3389),
            ('mstsc', 3389),
            ('remote', 3389),
            # SSH
            ('ssh', 22),
            ('sftp', 22),
            # HTTP/Web
            ('http', 80),
            ('web', 80),
            ('nginx', 80),
            ('apache', 80),
            # Docker
            ('docker', 9000),
            # MySQL
            ('mysql', 3306),
            # PostgreSQL
            ('postgres', 5432),
            ('pgsql', 5432),
            # Redis
            ('redis', 6379),
            # MongoDB
            ('mongo', 27017),
            # FTP
            ('ftp', 21),
            # SMTP
            ('smtps', 465),
            ('smtp', 25),
            # IMAP/POP3
            ('imaps', 993),
            ('imap', 143),
            ('pop3s', 995),
            ('pop3', 110),
            # DNS
            ('dns', 53),
            # NTP
            ('ntp', 123),
            # Game servers
            ('csgo', 27015),
            ('cs', 27015),
            ('mc', 25565),
            # Other common services
            ('es', 9200),
            ('kibana', 5601),
            ('grafana', 3000),
            ('jenkins', 8080),
            ('tomcat', 8080),
        ]
        
        # 将代理名称转为小写进行匹配
        name_lower = proxy_name.lower()
        
        # 先检查是否包含端口号（例如：dlyy_http_8080）
        import re
        port_pattern = re.search(r'_(\d{2,5})$', name_lower)
        if port_pattern:
            try:
                port = int(port_pattern.group(1))
                if 1 <= port <= 65535:
                    return port
            except (ValueError, AttributeError):
                pass
        
        # 使用单词边界匹配，优先匹配完整单词
        # 先尝试完整单词匹配（使用下划线或开头/结尾作为边界）
        for keyword, port in port_mappings:
            # 尝试匹配完整单词（前后是下划线或字符串开头/结尾）
            pattern = r'(^|_)' + re.escape(keyword) + r'($|_)'
            if re.search(pattern, name_lower):
                return port
        
        # 如果没有完整单词匹配，再尝试包含匹配（按顺序，长关键字优先）
        for keyword, port in port_mappings:
            if keyword in name_lower:
                return port
        
        # 如果无法识别，返回 0
        return 0
    
    def __repr__(self):
        return f"<Proxy(id={self.id}, name='{self.name}', group='{self.group_name}', type='{self.proxy_type}', status='{self.status}')>"

