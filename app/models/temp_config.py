"""临时配置模型"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class TempConfig(Base):
    """临时配置表（用于存储选择代理生成的临时配置）"""
    __tablename__ = "temp_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(String(50), unique=True, nullable=False, index=True)  # 随机生成的配置ID
    server_name = Column(String(100), nullable=False)
    group_name = Column(String(100), nullable=False)  # 实际上是临时组名（包含随机ID）
    config_content = Column(Text, nullable=False)  # 配置文件内容
    format = Column(String(10), default="ini", nullable=False)  # ini 或 toml
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # 过期时间
    
    def __repr__(self):
        return f"<TempConfig(id={self.config_id}, server='{self.server_name}', expires={self.expires_at})>"
    
    @property
    def is_expired(self):
        """检查是否已过期"""
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def create_temp_config(cls, server_name: str, group_name: str, config_content: str, format: str = "ini", hours: int = 24):
        """创建临时配置
        
        Args:
            server_name: 服务器名称
            group_name: 临时分组名称（包含随机ID）
            config_content: 配置内容
            format: 配置格式
            hours: 有效期（小时）
            
        Returns:
            TempConfig 实例
        """
        import secrets
        config_id = secrets.token_urlsafe(16)
        expires_at = datetime.utcnow() + timedelta(hours=hours)
        
        return cls(
            config_id=config_id,
            server_name=server_name,
            group_name=group_name,
            config_content=config_content,
            format=format,
            expires_at=expires_at
        )

