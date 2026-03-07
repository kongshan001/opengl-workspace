"""
配置管理模块
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 9527
    token: str = ""


@dataclass
class WebConfig:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 9528
    username: str = "admin"
    password: str = ""  # 空则自动生成


@dataclass
class TLSConfig:
    enabled: bool = False
    cert_file: str = ""
    key_file: str = ""


@dataclass
class LogConfig:
    level: str = "INFO"
    file: str = "/var/log/remote-shell/remote-shell.log"


@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    web: WebConfig = field(default_factory=WebConfig)
    tls: TLSConfig = field(default_factory=TLSConfig)
    log: LogConfig = field(default_factory=LogConfig)
    public_ip: str = ""
    
    @classmethod
    def load(cls, path: str) -> 'Config':
        """从文件加载配置"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        config = cls()
        
        if 'server' in data:
            config.server = ServerConfig(**data['server'])
        if 'web' in data:
            config.web = WebConfig(**data['web'])
        if 'tls' in data:
            config.tls = TLSConfig(**data['tls'])
        if 'log' in data:
            config.log = LogConfig(**data['log'])
        if 'public_ip' in data:
            config.public_ip = data['public_ip']
        
        # 自动生成 token 和密码
        if not config.server.token:
            import secrets
            config.server.token = secrets.token_hex(16)
        
        if not config.web.password:
            import secrets
            config.web.password = secrets.token_hex(8)
        
        return config
    
    def save(self, path: str):
        """保存配置到文件"""
        data = {
            'server': {
                'host': self.server.host,
                'port': self.server.port,
                'token': self.server.token
            },
            'web': {
                'enabled': self.web.enabled,
                'host': self.web.host,
                'port': self.web.port,
                'username': self.web.username,
                'password': self.web.password
            },
            'tls': {
                'enabled': self.tls.enabled,
                'cert_file': self.tls.cert_file,
                'key_file': self.tls.key_file
            },
            'log': {
                'level': self.log.level,
                'file': self.log.file
            },
            'public_ip': self.public_ip
        }
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def get_connect_url(self) -> str:
        """获取连接 URL"""
        host = self.public_ip or "YOUR_SERVER_IP"
        return f"{host}:{self.server.port}"
    
    def get_web_url(self) -> str:
        """获取 Web 管理界面 URL"""
        host = self.public_ip or "YOUR_SERVER_IP"
        protocol = "https" if self.tls.enabled else "http"
        return f"{protocol}://{host}:{self.web.port}"
