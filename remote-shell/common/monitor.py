"""
系统监控模块
CPU、内存、磁盘、进程监控
"""

import os
import time
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CPUInfo:
    usage: float
    cores: int
    load_avg: List[float]


@dataclass
class MemoryInfo:
    total: int
    used: int
    free: int
    percent: float


@dataclass
class DiskInfo:
    total: int
    used: int
    free: int
    percent: float
    mount_point: str


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    command: str


class SystemMonitor:
    """系统监控"""
    
    @staticmethod
    async def get_cpu_info() -> CPUInfo:
        """获取 CPU 信息"""
        # CPU 使用率
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                values = [int(x) for x in line.split()[1:8]]
                idle = values[3]
                total = sum(values)
                
                # 等待一下再读取
                await asyncio.sleep(0.1)
                
                with open('/proc/stat', 'r') as f:
                    line = f.readline()
                    new_values = [int(x) for x in line.split()[1:8]]
                    new_idle = new_values[3]
                    new_total = sum(new_values)
                
                idle_delta = new_idle - idle
                total_delta = new_total - total
                usage = 100.0 * (1.0 - idle_delta / total_delta) if total_delta > 0 else 0
        except:
            usage = 0
        
        # CPU 核心数
        cores = os.cpu_count() or 1
        
        # 负载
        try:
            with open('/proc/loadavg', 'r') as f:
                load_avg = [float(x) for x in f.read().split()[:3]]
        except:
            load_avg = [0, 0, 0]
        
        return CPUInfo(
            usage=round(usage, 1),
            cores=cores,
            load_avg=load_avg
        )
    
    @staticmethod
    def get_memory_info() -> MemoryInfo:
        """获取内存信息"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                info = {}
                for line in lines:
                    parts = line.split()
                    key = parts[0].rstrip(':')
                    value = int(parts[1])
                    info[key] = value
                
                total = info.get('MemTotal', 0) * 1024
                free = info.get('MemFree', 0) * 1024
                buffers = info.get('Buffers', 0) * 1024
                cached = info.get('Cached', 0) * 1024
                used = total - free - buffers - cached
                percent = 100.0 * used / total if total > 0 else 0
                
                return MemoryInfo(
                    total=total,
                    used=used,
                    free=free,
                    percent=round(percent, 1)
                )
        except:
            return MemoryInfo(total=0, used=0, free=0, percent=0)
    
    @staticmethod
    def get_disk_info() -> List[DiskInfo]:
        """获取磁盘信息"""
        disks = []
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        device, mount = parts[0], parts[1]
                        # 只关心真实设备
                        if device.startswith('/dev/'):
                            stat = os.statvfs(mount)
                            total = stat.f_blocks * stat.f_frsize
                            free = stat.f_bavail * stat.f_frsize
                            used = total - free
                            percent = 100.0 * used / total if total > 0 else 0
                            
                            disks.append(DiskInfo(
                                total=total,
                                used=used,
                                free=free,
                                percent=round(percent, 1),
                                mount_point=mount
                            ))
        except:
            pass
        return disks
    
    @staticmethod
    async def get_processes(limit: int = 20, sort_by: str = "cpu") -> List[ProcessInfo]:
        """获取进程列表"""
        processes = []
        
        try:
            for pid_dir in os.listdir('/proc'):
                if not pid_dir.isdigit():
                    continue
                
                try:
                    pid = int(pid_dir)
                    proc_path = f'/proc/{pid}'
                    
                    # 读取命令
                    with open(f'{proc_path}/comm', 'r') as f:
                        name = f.read().strip()
                    
                    # 读取命令行
                    try:
                        with open(f'{proc_path}/cmdline', 'r') as f:
                            cmdline = f.read().replace('\x00', ' ').strip()[:100]
                    except:
                        cmdline = name
                    
                    # 读取状态
                    with open(f'{proc_path}/stat', 'r') as f:
                        stat = f.read().split()
                        status = stat[2]
                    
                    # 简化的 CPU 和内存使用
                    processes.append(ProcessInfo(
                        pid=pid,
                        name=name,
                        cpu_percent=0,  # 需要采样计算
                        memory_percent=0,
                        status=status,
                        command=cmdline
                    ))
                    
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    continue
            
            # 限制数量
            processes = processes[:limit]
            
        except Exception as e:
            print(f"获取进程列表失败: {e}")
        
        return processes
    
    @staticmethod
    async def get_system_info() -> dict:
        """获取完整系统信息"""
        cpu = await SystemMonitor.get_cpu_info()
        memory = SystemMonitor.get_memory_info()
        disks = SystemMonitor.get_disk_info()
        
        # 获取主机名
        try:
            with open('/etc/hostname', 'r') as f:
                hostname = f.read().strip()
        except:
            hostname = "unknown"
        
        # 获取系统时间
        now = datetime.now()
        
        # 获取运行时间
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
                uptime_days = uptime_seconds / 86400
        except:
            uptime_days = 0
        
        return {
            "hostname": hostname,
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_days": round(uptime_days, 1),
            "cpu": {
                "usage": cpu.usage,
                "cores": cpu.cores,
                "load_avg": cpu.load_avg
            },
            "memory": {
                "total": memory.total,
                "used": memory.used,
                "free": memory.free,
                "percent": memory.percent
            },
            "disks": [
                {
                    "mount": d.mount_point,
                    "total": d.total,
                    "used": d.used,
                    "free": d.free,
                    "percent": d.percent
                }
                for d in disks
            ]
        }
    
    @staticmethod
    def format_bytes(bytes: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} PB"
