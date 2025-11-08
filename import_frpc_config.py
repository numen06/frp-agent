#!/usr/bin/env python3
"""
frpc 配置文件导入工具

使用方式:
    python3 import_frpc_config.py --help
    python3 import_frpc_config.py frpc.ini --server-id 1 --token YOUR_TOKEN
    python3 import_frpc_config.py frpc.toml --format toml --group production
"""

import argparse
import json
import sys
import os
from pathlib import Path
import requests


def read_config_file(file_path: str) -> str:
    """读取配置文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 不存在", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取文件失败: {e}", file=sys.stderr)
        sys.exit(1)


def detect_format(file_path: str) -> str:
    """根据文件扩展名检测配置格式"""
    ext = Path(file_path).suffix.lower()
    if ext == '.ini':
        return 'ini'
    elif ext == '.toml':
        return 'toml'
    else:
        print(f"警告: 无法从扩展名 '{ext}' 判断格式，请使用 --format 参数指定", file=sys.stderr)
        return None


def import_config(api_url: str, token: str, content: str, 
                 format_type: str, server_id: int, group_name: str = None) -> dict:
    """通过 API 导入配置"""
    
    # 构建请求数据
    data = {
        "content": content,
        "format": format_type,
        "frps_server_id": server_id
    }
    
    if group_name:
        data["group_name"] = group_name
    
    # 构建请求头
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 发送请求
    try:
        response = requests.post(
            f"{api_url}/api/config/import/text",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"错误: 无法连接到服务器 {api_url}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("错误: 请求超时", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"错误: HTTP {e.response.status_code}", file=sys.stderr)
        try:
            error_detail = e.response.json()
            print(f"详情: {error_detail.get('detail', '未知错误')}", file=sys.stderr)
        except:
            print(f"详情: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def login(api_url: str, username: str, password: str) -> str:
    """登录并获取 token"""
    try:
        response = requests.post(
            f"{api_url}/api/auth/login",
            data={
                "username": username,
                "password": password
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        print(f"错误: 登录失败: {e}", file=sys.stderr)
        sys.exit(1)


def print_result(result: dict):
    """美化输出结果"""
    if result.get("success"):
        print("✓ 导入成功")
        print(f"\n{result.get('message', '')}")
        
        stats = result.get("stats", {})
        print(f"\n统计信息:")
        print(f"  总计: {stats.get('total', 0)}")
        print(f"  新增: {stats.get('created', 0)}")
        print(f"  更新: {stats.get('updated', 0)}")
        print(f"  失败: {stats.get('failed', 0)}")
        
        errors = stats.get("errors", [])
        if errors:
            print(f"\n失败详情:")
            for error in errors:
                print(f"  - {error.get('proxy_name', 'unknown')}: {error.get('error', '')}")
    else:
        print("✗ 导入失败", file=sys.stderr)
        print(f"\n{result.get('message', '未知错误')}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='frpc 配置文件导入工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用 token 导入 INI 配置
  %(prog)s frpc.ini --token YOUR_TOKEN_HERE
  
  # 使用用户名密码登录并导入
  %(prog)s frpc.ini --username admin --password secret
  
  # 导入 TOML 配置到指定服务器和分组
  %(prog)s frpc.toml --format toml --server-id 2 --group production
  
  # 指定 API 地址
  %(prog)s frpc.ini --url http://192.168.1.100:8000 --token YOUR_TOKEN
        """
    )
    
    parser.add_argument(
        'config_file',
        help='frpc 配置文件路径 (.ini 或 .toml)'
    )
    
    parser.add_argument(
        '--url',
        default='http://localhost:8000',
        help='frp-agent API 地址 (默认: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--server-id',
        type=int,
        default=1,
        help='frps 服务器 ID (默认: 1)'
    )
    
    parser.add_argument(
        '--format',
        choices=['ini', 'toml'],
        help='配置文件格式 (如果不指定，会根据文件扩展名自动判断)'
    )
    
    parser.add_argument(
        '--group',
        dest='group_name',
        help='分组名称 (可选，如果不指定会从代理名称自动解析)'
    )
    
    # 认证相关参数
    auth_group = parser.add_mutually_exclusive_group(required=True)
    auth_group.add_argument(
        '--token',
        help='认证 Token'
    )
    auth_group.add_argument(
        '--username',
        help='用户名 (需要配合 --password 使用)'
    )
    
    parser.add_argument(
        '--password',
        help='密码 (配合 --username 使用)'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='以 JSON 格式输出结果'
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if args.username and not args.password:
        parser.error("--username 需要配合 --password 使用")
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config_file):
        print(f"错误: 配置文件 '{args.config_file}' 不存在", file=sys.stderr)
        sys.exit(1)
    
    # 检测配置格式
    format_type = args.format
    if not format_type:
        format_type = detect_format(args.config_file)
        if not format_type:
            parser.error("无法自动判断配置格式，请使用 --format 参数指定")
    
    # 获取 token
    token = args.token
    if args.username:
        if not args.json:
            print(f"正在登录...")
        token = login(args.url, args.username, args.password)
        if not args.json:
            print("✓ 登录成功\n")
    
    # 读取配置文件
    if not args.json:
        print(f"正在读取配置文件: {args.config_file}")
    content = read_config_file(args.config_file)
    
    # 导入配置
    if not args.json:
        print(f"正在导入配置 (格式: {format_type}, 服务器: {args.server_id})...")
    
    result = import_config(
        api_url=args.url,
        token=token,
        content=content,
        format_type=format_type,
        server_id=args.server_id,
        group_name=args.group_name
    )
    
    # 输出结果
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print()
        print_result(result)


if __name__ == '__main__':
    main()

