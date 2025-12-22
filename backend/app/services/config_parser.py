"""frpc 配置文件解析服务"""
import configparser
import toml
from typing import List, Dict, Any
from io import StringIO


class ConfigParser:
    """配置文件解析器"""
    
    @staticmethod
    def parse_ini_config(content: str) -> List[Dict[str, Any]]:
        """解析 INI 格式的 frpc 配置文件
        
        Args:
            content: INI 配置文件内容
            
        Returns:
            代理配置列表，每个代理包含 name, type, local_ip, local_port, remote_port 等信息
        """
        proxies = []
        
        try:
            config = configparser.ConfigParser()
            config.read_string(content)
            
            # 遍历所有 section（除了 common）
            for section in config.sections():
                if section.lower() == 'common':
                    continue
                
                proxy_data = {
                    'name': section,
                    'proxy_type': config.get(section, 'type', fallback='tcp'),
                    'local_ip': config.get(section, 'local_ip', fallback='127.0.0.1'),
                    'local_port': None,
                    'remote_port': None,
                    'custom_domains': None,
                }
                
                # 解析 local_port（必需）
                if config.has_option(section, 'local_port'):
                    try:
                        proxy_data['local_port'] = int(config.get(section, 'local_port'))
                    except ValueError:
                        continue  # 跳过无效的端口配置
                else:
                    continue  # 没有 local_port 的配置无效
                
                # 解析 remote_port（可选，TCP/UDP 类型需要）
                if config.has_option(section, 'remote_port'):
                    try:
                        proxy_data['remote_port'] = int(config.get(section, 'remote_port'))
                    except ValueError:
                        pass
                
                # 解析 custom_domains（可选，HTTP/HTTPS 类型）
                if config.has_option(section, 'custom_domains'):
                    proxy_data['custom_domains'] = config.get(section, 'custom_domains')
                
                # 解析 subdomain（可选，HTTP/HTTPS 类型）
                if config.has_option(section, 'subdomain'):
                    proxy_data['subdomain'] = config.get(section, 'subdomain')
                
                proxies.append(proxy_data)
                
        except Exception as e:
            raise ValueError(f"解析 INI 配置文件失败: {str(e)}")
        
        return proxies
    
    @staticmethod
    def parse_toml_config(content: str) -> List[Dict[str, Any]]:
        """解析 TOML 格式的 frpc 配置文件
        
        Args:
            content: TOML 配置文件内容
            
        Returns:
            代理配置列表，每个代理包含 name, type, local_ip, local_port, remote_port 等信息
        """
        proxies = []
        
        try:
            config = toml.loads(content)
            
            # TOML 格式中代理配置在 proxies 数组中
            proxy_list = config.get('proxies', [])
            
            for proxy in proxy_list:
                # 获取代理名称
                name = proxy.get('name')
                if not name:
                    continue
                
                # 解析 local_port（必需）
                local_port = proxy.get('localPort') or proxy.get('local_port')
                if not local_port:
                    continue  # 没有 local_port 的配置无效
                
                proxy_data = {
                    'name': name,
                    'proxy_type': proxy.get('type', 'tcp'),
                    'local_ip': proxy.get('localIP') or proxy.get('local_ip', '127.0.0.1'),
                    'local_port': int(local_port),
                    'remote_port': None,
                    'custom_domains': None,
                }
                
                # 解析 remote_port（可选，TCP/UDP 类型需要）
                remote_port = proxy.get('remotePort') or proxy.get('remote_port')
                if remote_port:
                    try:
                        proxy_data['remote_port'] = int(remote_port)
                    except ValueError:
                        pass
                
                # 解析 customDomains（可选，HTTP/HTTPS 类型）
                custom_domains = proxy.get('customDomains') or proxy.get('custom_domains')
                if custom_domains:
                    if isinstance(custom_domains, list):
                        proxy_data['custom_domains'] = ','.join(custom_domains)
                    else:
                        proxy_data['custom_domains'] = str(custom_domains)
                
                # 解析 subdomain（可选，HTTP/HTTPS 类型）
                subdomain = proxy.get('subdomain')
                if subdomain:
                    proxy_data['subdomain'] = subdomain
                
                proxies.append(proxy_data)
                
        except Exception as e:
            raise ValueError(f"解析 TOML 配置文件失败: {str(e)}")
        
        return proxies
    
    @staticmethod
    def parse_config(content: str, file_extension: str) -> List[Dict[str, Any]]:
        """根据文件扩展名自动选择解析器
        
        Args:
            content: 配置文件内容
            file_extension: 文件扩展名（如 '.ini' 或 '.toml'）
            
        Returns:
            代理配置列表
        """
        file_extension = file_extension.lower().strip('.')
        
        if file_extension == 'ini':
            return ConfigParser.parse_ini_config(content)
        elif file_extension == 'toml':
            return ConfigParser.parse_toml_config(content)
        else:
            raise ValueError(f"不支持的配置文件格式: {file_extension}，仅支持 ini 和 toml")

