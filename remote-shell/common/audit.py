"""
审计日志模块
记录操作日志、登录日志，支持日志轮转和查询
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import gzip
import shutil


class AuditEventType(Enum):
    """审计事件类型"""
    # 认证相关
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    
    # 命令执行
    COMMAND_EXEC = "command_exec"
    COMMAND_SUCCESS = "command_success"
    COMMAND_FAILED = "command_failed"
    
    # 文件操作
    FILE_LIST = "file_list"
    FILE_DOWNLOAD = "file_download"
    FILE_UPLOAD = "file_upload"
    
    # 隧道操作
    TUNNEL_CREATE = "tunnel_create"
    TUNNEL_REMOVE = "tunnel_remove"
    
    # 用户管理
    USER_CREATE = "user_create"
    USER_DELETE = "user_delete"
    USER_PASSWORD_CHANGE = "user_password_change"
    
    # 系统事件
    SERVER_START = "server_start"
    SERVER_STOP = "server_stop"
    CLIENT_CONNECT = "client_connect"
    CLIENT_DISCONNECT = "client_disconnect"


@dataclass
class AuditEvent:
    """审计事件"""
    timestamp: float
    event_type: str
    username: str
    ip_address: str
    description: str
    details: Dict[str, Any]
    success: bool = True
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": self.event_type,
            "username": self.username,
            "ip_address": self.ip_address,
            "description": self.description,
            "details": self.details,
            "success": self.success
        }


class AuditLogger:
    """审计日志记录器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        log_dir: str = "/var/log/remote-shell/audit",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        max_files: int = 10,
        retention_days: int = 30
    ):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.log_dir = log_dir
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.retention_days = retention_days
        self.current_file: Optional[str] = None
        self.current_size: int = 0
        self._file_lock = threading.Lock()
        
        os.makedirs(log_dir, exist_ok=True)
        
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # 同时输出到控制台
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s [AUDIT] %(message)s'
            ))
            self.logger.addHandler(console_handler)
        
        self._initialized = True
    
    def _get_log_file(self) -> str:
        """获取当前日志文件路径"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"audit-{today}.log")
    
    def _rotate_if_needed(self):
        """检查并执行日志轮转"""
        log_file = self._get_log_file()
        
        # 检查是否需要压缩旧日志
        if self.current_file and self.current_file != log_file:
            self._compress_old_log(self.current_file)
        
        # 检查当前文件大小
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            if size >= self.max_file_size:
                # 分割大文件
                base, ext = os.path.splitext(log_file)
                index = 1
                while os.path.exists(f"{base}.{index}{ext}"):
                    index += 1
                new_file = f"{base}.{index}{ext}"
                shutil.move(log_file, new_file)
        
        self.current_file = log_file
    
    def _compress_old_log(self, log_file: str):
        """压缩旧日志文件"""
        if not os.path.exists(log_file):
            return
        
        gz_file = log_file + ".gz"
        if os.path.exists(gz_file):
            return
        
        try:
            with open(log_file, 'rb') as f_in:
                with gzip.open(gz_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(log_file)
        except Exception as e:
            self.logger.error(f"压缩日志失败: {e}")
    
    def _cleanup_old_logs(self):
        """清理过期日志"""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        
        for filename in os.listdir(self.log_dir):
            filepath = os.path.join(self.log_dir, filename)
            
            # 检查文件修改时间
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if mtime < cutoff:
                    os.remove(filepath)
                    self.logger.info(f"删除过期日志: {filename}")
            except Exception as e:
                self.logger.error(f"清理日志失败: {e}")
    
    def log(
        self,
        event_type: AuditEventType,
        username: str = "",
        ip_address: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
        success: bool = True
    ):
        """记录审计事件"""
        event = AuditEvent(
            timestamp=time.time(),
            event_type=event_type.value,
            username=username,
            ip_address=ip_address,
            description=description,
            details=details or {},
            success=success
        )
        
        with self._file_lock:
            self._rotate_if_needed()
            
            log_file = self._get_log_file()
            line = json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(line)
            
            # 输出到控制台
            status = "✓" if success else "✗"
            self.logger.info(
                f"[{status}] {event_type.value} | {username}@{ip_address} | {description}"
            )
        
        # 定期清理
        if int(time.time()) % 3600 == 0:  # 每小时检查一次
            self._cleanup_old_logs()
    
    def query(
        self,
        event_type: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: Optional[bool] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """查询审计日志"""
        results = []
        
        # 获取所有日志文件（按日期倒序）
        log_files = sorted(
            [f for f in os.listdir(self.log_dir) if f.startswith("audit-") and f.endswith(".log")],
            reverse=True
        )
        
        count = 0
        
        for filename in log_files:
            filepath = os.path.join(self.log_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            
                            # 应用过滤条件
                            if event_type and event.get("event_type") != event_type:
                                continue
                            if username and event.get("username") != username:
                                continue
                            if ip_address and event.get("ip_address") != ip_address:
                                continue
                            if success is not None and event.get("success") != success:
                                continue
                            if start_time and event.get("timestamp", 0) < start_time:
                                continue
                            if end_time and event.get("timestamp", 0) > end_time:
                                continue
                            
                            # 跳过 offset
                            if offset > 0:
                                offset -= 1
                                continue
                            
                            results.append(event)
                            count += 1
                            
                            if count >= limit:
                                return results
                                
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                self.logger.error(f"读取日志文件失败: {e}")
        
        return results
    
    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """获取统计数据"""
        cutoff = time.time() - hours * 3600
        
        stats = {
            "total_events": 0,
            "successful": 0,
            "failed": 0,
            "by_type": {},
            "by_user": {},
            "by_ip": {},
            "unique_users": set(),
            "unique_ips": set()
        }
        
        for event in self.query(start_time=cutoff, limit=10000):
            stats["total_events"] += 1
            
            if event.get("success"):
                stats["successful"] += 1
            else:
                stats["failed"] += 1
            
            event_type = event.get("event_type", "unknown")
            stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1
            
            username = event.get("username", "")
            if username:
                stats["by_user"][username] = stats["by_user"].get(username, 0) + 1
                stats["unique_users"].add(username)
            
            ip = event.get("ip_address", "")
            if ip:
                stats["by_ip"][ip] = stats["by_ip"].get(ip, 0) + 1
                stats["unique_ips"].add(ip)
        
        stats["unique_users"] = len(stats["unique_users"])
        stats["unique_ips"] = len(stats["unique_ips"])
        
        return stats


# 全局单例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(**kwargs) -> AuditLogger:
    """获取审计日志记录器单例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(**kwargs)
    return _audit_logger


# 便捷方法
def audit_log(
    event_type: AuditEventType,
    username: str = "",
    ip_address: str = "",
    description: str = "",
    details: Optional[Dict[str, Any]] = None,
    success: bool = True
):
    """记录审计事件（便捷方法）"""
    logger = get_audit_logger()
    logger.log(event_type, username, ip_address, description, details, success)
