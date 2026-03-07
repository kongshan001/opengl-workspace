"""
用户管理模块
支持多用户、权限控制
"""

import json
import os
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class Permission(Enum):
    """权限类型"""
    EXEC = "exec"           # 执行命令
    FILE_READ = "file_read" # 读取文件
    FILE_WRITE = "file_write" # 写入文件
    ADMIN = "admin"         # 管理员权限


@dataclass
class User:
    """用户"""
    username: str
    password_hash: str
    permissions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    disabled: bool = False
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        return self.password_hash == self._hash_password(password)
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @classmethod
    def create(cls, username: str, password: str, permissions: List[str] = None) -> 'User':
        """创建用户"""
        return cls(
            username=username,
            password_hash=cls._hash_password(password),
            permissions=permissions or [Permission.EXEC.value, Permission.FILE_READ.value]
        )
    
    def has_permission(self, permission: str) -> bool:
        """检查权限"""
        if self.disabled:
            return False
        if Permission.ADMIN.value in self.permissions:
            return True
        return permission in self.permissions
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "permissions": self.permissions,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "disabled": self.disabled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """从字典创建"""
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            permissions=data.get("permissions", []),
            created_at=data.get("created_at", time.time()),
            last_login=data.get("last_login"),
            disabled=data.get("disabled", False)
        )


class UserManager:
    """用户管理器"""
    
    def __init__(self, config_path: str = None):
        self.users: Dict[str, User] = {}
        self.config_path = config_path or "/etc/remote-shell/users.json"
        self.sessions: Dict[str, str] = {}  # session_token -> username
        
        # 加载用户
        self._load()
        
        # 确保有管理员账户
        if "admin" not in self.users:
            self.create_user("admin", "admin123", [p.value for p in Permission])
    
    def _load(self):
        """加载用户数据"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for username, user_data in data.get("users", {}).items():
                        self.users[username] = User.from_dict(user_data)
            except Exception as e:
                print(f"[UserManager] 加载用户失败: {e}")
    
    def _save(self):
        """保存用户数据"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        data = {
            "users": {u: user.to_dict() for u, user in self.users.items()}
        }
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_user(self, username: str, password: str, permissions: List[str] = None) -> bool:
        """创建用户"""
        if username in self.users:
            return False
        
        user = User.create(username, password, permissions)
        self.users[username] = user
        self._save()
        return True
    
    def delete_user(self, username: str) -> bool:
        """删除用户"""
        if username not in self.users:
            return False
        
        del self.users[username]
        self._save()
        return True
    
    def update_password(self, username: str, new_password: str) -> bool:
        """更新密码"""
        if username not in self.users:
            return False
        
        self.users[username].password_hash = User._hash_password(new_password)
        self._save()
        return True
    
    def update_permissions(self, username: str, permissions: List[str]) -> bool:
        """更新权限"""
        if username not in self.users:
            return False
        
        self.users[username].permissions = permissions
        self._save()
        return True
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """认证用户，返回 session token"""
        user = self.users.get(username)
        if not user or user.disabled:
            return None
        
        if not user.check_password(password):
            return None
        
        # 生成 session token
        import secrets
        token = secrets.token_hex(32)
        self.sessions[token] = username
        
        # 更新最后登录时间
        user.last_login = time.time()
        self._save()
        
        return token
    
    def validate_session(self, token: str) -> Optional[str]:
        """验证 session，返回用户名"""
        return self.sessions.get(token)
    
    def logout(self, token: str):
        """登出"""
        if token in self.sessions:
            del self.sessions[token]
    
    def get_user(self, username: str) -> Optional[User]:
        """获取用户"""
        return self.users.get(username)
    
    def list_users(self) -> List[dict]:
        """列出所有用户"""
        return [
            {
                "username": u,
                "permissions": user.permissions,
                "disabled": user.disabled,
                "last_login": user.last_login
            }
            for u, user in self.users.items()
        ]
