"""
API 代理 - 转发请求到上游模型
"""
import asyncio
import time
import uuid
import httpx
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime

from .models import UpstreamKey, User, RequestRecord
from .storage import db
from .load_balancer import load_balancer


class ProxyError(Exception):
    """代理错误"""
    pass


class APIClient:
    """
    上游 API 客户端
    
    支持 OpenAI 兼容的 API 格式
    """

    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


class ProxyService:
    """代理服务"""

    def __init__(self):
        self.api_client = APIClient()
        self._user_locks: Dict[str, asyncio.Lock] = {}

    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        """获取用户锁"""
        if user_id not in self._user_locks:
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]

    async def chat_completion(
        self,
        user: User,
        messages: list,
        model: str = "gpt-3.5-turbo",
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        聊天完成接口
        
        Args:
            user: 用户对象
            messages: 消息列表
            model: 模型名称
            stream: 是否流式
            **kwargs: 其他参数 (temperature, max_tokens 等)
        
        Returns:
            API 响应
        """
        start_time = time.time()
        upstream_key = None
        record = None

        # 检查用户配额
        if user.used_tokens >= user.monthly_quota:
            raise ProxyError("月度配额已用尽")

        # 获取用户锁，确保单用户并发限制
        user_lock = self._get_user_lock(user.id)
        
        async with user_lock:
            # 检查用户并发（双重检查）
            if user.current_concurrent >= user.max_concurrent:
                raise ProxyError("并发数已达上限，请稍后重试")

            # 更新用户并发数
            await db.update_user_concurrent(user.id, +1)
            user.current_concurrent += 1

            try:
                # 获取可用的上游 Key
                upstream_key = await load_balancer.acquire()
                if upstream_key is None:
                    raise ProxyError("服务繁忙，所有上游通道均忙碌，请稍后重试")

                load_balancer.stats.total_requests += 1

                # 构建请求
                request_body = {
                    "model": model,
                    "messages": messages,
                    "stream": stream,
                    **kwargs
                }

                # 发送请求
                client = await self.api_client.get_client()
                response = await client.post(
                    f"{upstream_key.base_url}/chat/completions",
                    json=request_body,
                    headers={
                        "Authorization": f"Bearer {upstream_key.api_key}",
                        "Content-Type": "application/json"
                    }
                )

                latency_ms = (time.time() - start_time) * 1000

                if response.status_code != 200:
                    load_balancer.stats.failed_requests += 1
                    error_msg = response.text[:500]
                    raise ProxyError(f"上游 API 错误 ({response.status_code}): {error_msg}")

                result = response.json()

                # 记录使用量
                usage = result.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)

                # 创建请求记录
                record = RequestRecord(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    upstream_key_name=upstream_key.name,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    created_at=datetime.now(),
                    latency_ms=latency_ms,
                    status="success"
                )
                await db.create_request(record)

                # 更新用户 token 用量
                await db.add_user_tokens(user.id, prompt_tokens + completion_tokens)

                load_balancer.stats.successful_requests += 1

                return result

            except httpx.TimeoutException:
                load_balancer.stats.failed_requests += 1
                raise ProxyError("上游 API 请求超时")

            except httpx.RequestError as e:
                load_balancer.stats.failed_requests += 1
                raise ProxyError(f"网络错误: {str(e)}")

            finally:
                # 释放上游 Key
                if upstream_key:
                    await load_balancer.release(upstream_key.name)

                # 释放用户并发槽位
                await db.update_user_concurrent(user.id, -1)
                user.current_concurrent -= 1

    async def chat_completion_stream(
        self,
        user: User,
        messages: list,
        model: str = "gpt-3.5-turbo",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天完成接口
        
        Yields:
            SSE 格式的数据块
        """
        start_time = time.time()
        upstream_key = None

        # 检查用户配额
        if user.used_tokens >= user.monthly_quota:
            yield f"data: {ProxyError('月度配额已用尽')}\n\n"
            return

        user_lock = self._get_user_lock(user.id)

        async with user_lock:
            if user.current_concurrent >= user.max_concurrent:
                yield f"data: {ProxyError('并发数已达上限')}\n\n"
                return

            await db.update_user_concurrent(user.id, +1)
            user.current_concurrent += 1

            try:
                upstream_key = await load_balancer.acquire()
                if upstream_key is None:
                    yield f"data: {ProxyError('服务繁忙')}\n\n"
                    return

                load_balancer.stats.total_requests += 1

                request_body = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    **kwargs
                }

                client = await self.api_client.get_client()
                
                async with client.stream(
                    "POST",
                    f"{upstream_key.base_url}/chat/completions",
                    json=request_body,
                    headers={
                        "Authorization": f"Bearer {upstream_key.api_key}",
                        "Content-Type": "application/json"
                    }
                ) as response:
                    if response.status_code != 200:
                        load_balancer.stats.failed_requests += 1
                        yield f"data: {ProxyError(f'上游错误: {response.status_code}')}\n\n"
                        return

                    async for chunk in response.aiter_text():
                        yield chunk

                load_balancer.stats.successful_requests += 1

            except Exception as e:
                load_balancer.stats.failed_requests += 1
                yield f"data: {ProxyError(str(e))}\n\n"

            finally:
                if upstream_key:
                    await load_balancer.release(upstream_key.name)
                await db.update_user_concurrent(user.id, -1)
                user.current_concurrent -= 1

    async def close(self):
        """关闭客户端"""
        await self.api_client.close()


# 全局代理服务实例
proxy_service = ProxyService()
