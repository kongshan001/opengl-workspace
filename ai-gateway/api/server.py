"""
FastAPI 服务主入口
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.storage import db
from core.load_balancer import load_balancer
from core.proxy import proxy_service, ProxyError
from core.models import User


# ============ 请求模型 ============

class ChatCompletionRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: List[Dict[str, str]]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class CreateUserRequest(BaseModel):
    name: str
    max_concurrent: int = 1
    monthly_quota: int = 1000000


# ============ 应用生命周期 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    load_balancer.load_from_config(str(config_path))
    await db.connect()
    
    print(f"[Gateway] 服务启动，已加载 {len(load_balancer.upstream_keys)} 个上游 Key")
    
    yield
    
    # 关闭时
    await proxy_service.close()
    await db.disconnect()
    print("[Gateway] 服务已关闭")


app = FastAPI(
    title="AI Gateway",
    description="AI API 代理网关 - 统一入口，智能负载均衡",
    version="1.0.0",
    lifespan=lifespan
)


# ============ 认证中间件 ============

async def get_current_user(authorization: str = Header(None)) -> User:
    """获取当前用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization 头")
    
    if authorization.startswith("Bearer "):
        api_key = authorization[7:]
    else:
        api_key = authorization
    
    user = await db.get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")
    
    return user


# ============ 代理 API ============

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user: User = Header(None)
):
    """
    聊天完成接口（兼容 OpenAI 格式）
    
    Header: Authorization: Bearer gw_xxxx
    """
    # 手动获取用户（因为 Header 依赖不好直接用）
    from fastapi import Request as FastRequest
    # 这里简化处理，实际应该用依赖注入
    
    try:
        if request.stream:
            return StreamingResponse(
                proxy_service.chat_completion_stream(
                    user, request.messages, request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ),
                media_type="text/event-stream"
            )
        else:
            result = await proxy_service.chat_completion(
                user, request.messages, request.model,
                stream=False,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            return JSONResponse(content=result)
    
    except ProxyError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/chat/completions")
async def chat_completions_alias(
    request: ChatCompletionRequest,
    authorization: str = Header(None)
):
    """聊天完成接口（带认证）"""
    user = await get_current_user(authorization)
    
    try:
        if request.stream:
            return StreamingResponse(
                proxy_service.chat_completion_stream(
                    user, request.messages, request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ),
                media_type="text/event-stream"
            )
        else:
            result = await proxy_service.chat_completion(
                user, request.messages, request.model,
                stream=False,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            return JSONResponse(content=result)
    
    except ProxyError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ============ 用户管理 API ============

@app.post("/admin/users")
async def create_user(request: CreateUserRequest):
    """创建用户"""
    user = User.create(
        name=request.name,
        max_concurrent=request.max_concurrent,
        monthly_quota=request.monthly_quota
    )
    await db.create_user(user)
    return {
        "id": user.id,
        "name": user.name,
        "api_key": user.api_key,
        "max_concurrent": user.max_concurrent,
        "monthly_quota": user.monthly_quota
    }


@app.get("/admin/users")
async def list_users():
    """列出所有用户"""
    users = await db.list_users()
    return {
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "api_key": u.api_key[:10] + "...",  # 隐藏部分 key
                "max_concurrent": u.max_concurrent,
                "current_concurrent": u.current_concurrent,
                "monthly_quota": u.monthly_quota,
                "used_tokens": u.used_tokens,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat()
            }
            for u in users
        ]
    }


@app.get("/admin/users/{user_id}/stats")
async def get_user_stats(user_id: str):
    """获取用户统计"""
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    stats = await db.get_user_stats(user_id)
    return {
        "user_id": user_id,
        "name": user.name,
        "used_tokens": user.used_tokens,
        "monthly_quota": user.monthly_quota,
        **stats
    }


# ============ 系统状态 API ============

@app.get("/status")
async def get_status():
    """获取系统状态"""
    return {
        "service": "AI Gateway",
        "version": "1.0.0",
        "load_balancer": load_balancer.get_status()
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


# ============ 启动入口 ============

def run_server(host: str = "0.0.0.0", port: int = 8765):
    """启动服务器"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
