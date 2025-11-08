#!/usr/bin/env python3
"""
测试配置导入功能

这个脚本用于测试新添加的 curl 导入功能是否正常工作。
"""

import requests
import json
import sys

# 配置
API_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin@123"

# 测试用的 INI 配置
TEST_INI_CONFIG = """[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 6000

[web]
type = tcp
local_ip = 127.0.0.1
local_port = 80
remote_port = 8080
"""

# 测试用的 TOML 配置
TEST_TOML_CONFIG = """
[[proxies]]
name = "ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = 6000

[[proxies]]
name = "web"
type = "tcp"
localIP = "127.0.0.1"
localPort = 80
remotePort = 8080
"""


def login():
    """登录并获取 token"""
    print("正在登录...")
    try:
        response = requests.post(
            f"{API_URL}/api/auth/login",
            data={
                "username": USERNAME,
                "password": PASSWORD
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        print(f"✓ 登录成功")
        print(f"Token: {token[:20]}...")
        return token
    except requests.exceptions.ConnectionError:
        print(f"✗ 无法连接到服务器 {API_URL}")
        print("请确保服务器正在运行 (python app.py)")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 登录失败: {e}")
        sys.exit(1)


def test_import_ini(token):
    """测试导入 INI 配置"""
    print("\n" + "="*60)
    print("测试 1: 导入 INI 格式配置")
    print("="*60)
    
    data = {
        "content": TEST_INI_CONFIG,
        "format": "ini",
        "frps_server_id": 1,
        "group_name": "test"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/config/import/text",
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"HTTP 状态码: {response.status_code}")
        result = response.json()
        print(f"响应:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("success"):
            print("✓ INI 配置导入成功")
            return True
        else:
            print("✗ INI 配置导入失败")
            return False
            
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def test_import_toml(token):
    """测试导入 TOML 配置"""
    print("\n" + "="*60)
    print("测试 2: 导入 TOML 格式配置")
    print("="*60)
    
    data = {
        "content": TEST_TOML_CONFIG,
        "format": "toml",
        "frps_server_id": 1,
        "group_name": "test"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/config/import/text",
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"HTTP 状态码: {response.status_code}")
        result = response.json()
        print(f"响应:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("success"):
            print("✓ TOML 配置导入成功")
            return True
        else:
            print("✗ TOML 配置导入失败")
            return False
            
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def test_invalid_format(token):
    """测试无效格式"""
    print("\n" + "="*60)
    print("测试 3: 测试无效格式（应该返回错误）")
    print("="*60)
    
    data = {
        "content": TEST_INI_CONFIG,
        "format": "xml",  # 无效格式
        "frps_server_id": 1
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/config/import/text",
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"HTTP 状态码: {response.status_code}")
        result = response.json()
        print(f"响应:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if response.status_code == 400:
            print("✓ 正确拒绝了无效格式")
            return True
        else:
            print("✗ 没有正确处理无效格式")
            return False
            
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def test_missing_auth(token):
    """测试缺少认证"""
    print("\n" + "="*60)
    print("测试 4: 测试缺少认证（应该返回 401）")
    print("="*60)
    
    data = {
        "content": TEST_INI_CONFIG,
        "format": "ini",
        "frps_server_id": 1
    }
    
    headers = {
        "Content-Type": "application/json"
        # 故意不包含 Authorization 头
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/config/import/text",
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"HTTP 状态码: {response.status_code}")
        
        if response.status_code == 401:
            print("✓ 正确要求了认证")
            return True
        else:
            print("✗ 没有正确检查认证")
            return False
            
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("="*60)
    print("配置导入功能测试")
    print("="*60)
    
    # 登录
    token = login()
    
    # 运行测试
    results = []
    results.append(("导入 INI 配置", test_import_ini(token)))
    results.append(("导入 TOML 配置", test_import_toml(token)))
    results.append(("拒绝无效格式", test_invalid_format(token)))
    results.append(("要求认证", test_missing_auth(token)))
    
    # 显示测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
    
    # 计算通过率
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    pass_rate = (passed_count / total_count) * 100
    
    print(f"\n总计: {passed_count}/{total_count} 通过 ({pass_rate:.1f}%)")
    
    if passed_count == total_count:
        print("\n✓ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n✗ 部分测试失败")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)

