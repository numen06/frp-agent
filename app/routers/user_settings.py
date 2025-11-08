"""用户设置路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.auth import get_current_user
from app.models.user import User
from app.config import get_settings
import os

router = APIRouter(prefix="/api/settings", tags=["用户设置"])


class PasswordChange(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


class UserSettings(BaseModel):
    """用户设置响应"""
    username: str


@router.get("/user", response_model=UserSettings)
def get_user_settings(current_user: User = Depends(get_current_user)):
    """获取用户设置"""
    settings = get_settings()
    return {
        "username": settings.auth_username
    }


@router.post("/password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user)
):
    """修改密码"""
    settings = get_settings()
    
    # 验证旧密码
    if password_data.old_password != settings.auth_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 验证新密码
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码长度至少 6 位"
        )
    
    if password_data.new_password == password_data.old_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与旧密码相同"
        )
    
    # 更新 .env 文件
    try:
        update_env_file('AUTH_PASSWORD', password_data.new_password)
        return {
            "success": True,
            "message": "密码修改成功，请重新登录"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存失败: {str(e)}"
        )


def update_env_file(key: str, value: str, env_file: str = '.env'):
    """更新 .env 文件中的配置"""
    
    # 读取现有配置
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.splitlines(keepends=True)
    else:
        lines = []
    
    # 更新或添加配置
    key_found = False
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        # 检查是否是目标配置行（不是注释）
        if stripped and not stripped.startswith('#') and stripped.startswith(f'{key}='):
            new_lines.append(f'{key}={value}\n')
            key_found = True
        else:
            new_lines.append(line)
    
    # 如果没找到，添加到末尾
    if not key_found:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        new_lines.append(f'\n# 用户修改的配置\n')
        new_lines.append(f'{key}={value}\n')
    
    # 写回文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    # 更新环境变量
    os.environ[key] = value

