"""
负载均衡器 - 管理上游 Key 池和智能调度
"""
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
import random
import yaml
import os

from .models import UpstreamKey


@dataclass
class LoadBalancerStats:
    """负载均衡器统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0


class LoadBalancer:
    """
    负载均衡器
    
    策略:
    - least_loaded: 选择当前并发最少的 Key
    - round_robin: 轮询
    - random: 随机选择
    """

    def __init__(self, strategy: str = "least_loaded"):
        self.strategy = strategy
        self.upstream_keys: Dict[str, UpstreamKey] = {}
        self._key_order: List[str] = []  # 用于 round_robin
        self._current_index = 0
        self._lock = asyncio.Lock()
        self.stats = LoadBalancerStats()

    def load_from_config(self, config_path: str):
        """从配置文件加载上游 Key"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        for key_config in config.get('upstream_keys', []):
            # 支持环境变量替换
            api_key = key_config['api_key']
            if api_key.startswith('${') and api_key.endswith('}'):
                env_var = api_key[2:-1]
                api_key = os.environ.get(env_var, '')

            upstream = UpstreamKey(
                name=key_config['name'],
                provider=key_config['provider'],
                api_key=api_key,
                base_url=key_config['base_url'],
                max_concurrent=key_config.get('max_concurrent', 2),
                enabled=key_config.get('enabled', True)
            )
            self.upstream_keys[upstream.name] = upstream
            self._key_order.append(upstream.name)

        print(f"[LoadBalancer] 已加载 {len(self.upstream_keys)} 个上游 Key")

    def add_upstream(self, key: UpstreamKey):
        """添加上游 Key"""
        self.upstream_keys[key.name] = key
        if key.name not in self._key_order:
            self._key_order.append(key.name)

    def remove_upstream(self, name: str):
        """移除上游 Key"""
        if name in self.upstream_keys:
            del self.upstream_keys[name]
        if name in self._key_order:
            self._key_order.remove(name)

    async def acquire(self) -> Optional[UpstreamKey]:
        """
        获取一个可用的上游 Key
        
        返回 None 表示所有 Key 都忙
        """
        async with self._lock:
            available = [k for k in self.upstream_keys.values() if k.is_available]
            
            if not available:
                return None

            if self.strategy == "least_loaded":
                # 选择当前并发最少的
                selected = min(available, key=lambda k: k.current_concurrent)
            elif self.strategy == "round_robin":
                # 轮询，但跳过不可用的
                for _ in range(len(self._key_order)):
                    key_name = self._key_order[self._current_index % len(self._key_order)]
                    self._current_index += 1
                    if key_name in self.upstream_keys:
                        key = self.upstream_keys[key_name]
                        if key.is_available:
                            selected = key
                            break
                else:
                    return None
            else:  # random
                selected = random.choice(available)

            # 占用一个槽位
            selected.current_concurrent += 1
            return selected

    async def release(self, key_name: str):
        """释放上游 Key 的槽位"""
        async with self._lock:
            if key_name in self.upstream_keys:
                key = self.upstream_keys[key_name]
                key.current_concurrent = max(0, key.current_concurrent - 1)

    def get_status(self) -> Dict:
        """获取负载均衡器状态"""
        return {
            "strategy": self.strategy,
            "total_keys": len(self.upstream_keys),
            "enabled_keys": sum(1 for k in self.upstream_keys.values() if k.enabled),
            "keys": {
                name: {
                    "provider": key.provider,
                    "max_concurrent": key.max_concurrent,
                    "current_concurrent": key.current_concurrent,
                    "available_slots": key.available_slots,
                    "enabled": key.enabled
                }
                for name, key in self.upstream_keys.items()
            },
            "stats": {
                "total_requests": self.stats.total_requests,
                "successful": self.stats.successful_requests,
                "failed": self.stats.failed_requests
            }
        }

    async def set_key_enabled(self, name: str, enabled: bool) -> bool:
        """启用/禁用某个 Key"""
        if name in self.upstream_keys:
            self.upstream_keys[name].enabled = enabled
            return True
        return False


# 全局负载均衡器实例
load_balancer = LoadBalancer()
