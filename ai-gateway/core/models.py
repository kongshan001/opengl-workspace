"""
数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid
import hashlib


class Provider(Enum):
    JOINER = "joiner"
    OPENAI = "openai"
    CLAUDE = "claude"
    GLM = "glm"


@dataclass
class UpstreamKey:
    """上游 API Key"""
    name: str
    provider: str
    api_key: str
    base_url: str
    max_concurrent: int = 2
    enabled: bool = True
    current_concurrent: int = 0

    @property
    def available_slots(self) -> int:
        """剩余可用槽位"""
        if not self.enabled:
            return 0
        return max(0, self.max_concurrent - self.current_concurrent)

    @property
    def is_available(self) -> bool:
        """是否可用"""
        return self.enabled and self.available_slots > 0


@dataclass
class User:
    """用户"""
    id: str
    name: str
    api_key: str
    created_at: datetime
    max_concurrent: int = 1
    monthly_quota: int = 1000000
    used_tokens: int = 0
    is_active: bool = True
    current_concurrent: int = 0

    @classmethod
    def create(cls, name: str, max_concurrent: int = 1, monthly_quota: int = 1000000) -> "User":
        """创建新用户"""
        user_id = str(uuid.uuid4())
        # 生成 API Key: gw_xxxx 格式
        api_key = "gw_" + hashlib.sha256(f"{user_id}:{name}".encode()).hexdigest()[:32]
        return cls(
            id=user_id,
            name=name,
            api_key=api_key,
            created_at=datetime.now(),
            max_concurrent=max_concurrent,
            monthly_quota=monthly_quota
        )

    @property
    def available_slots(self) -> int:
        return max(0, self.max_concurrent - self.current_concurrent)

    @property
    def is_available(self) -> bool:
        return self.is_active and self.available_slots > 0 and self.used_tokens < self.monthly_quota


@dataclass
class RequestRecord:
    """请求记录"""
    id: str
    user_id: str
    upstream_key_name: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime
    latency_ms: float
    status: str  # success, failed, timeout

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
