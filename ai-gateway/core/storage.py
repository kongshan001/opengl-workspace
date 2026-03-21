"""
数据存储层 - 使用 SQLite
"""
import aiosqlite
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from .models import User, UpstreamKey, RequestRecord


class Database:
    """异步数据库管理"""

    def __init__(self, db_path: str = "data/gateway.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """连接数据库"""
        self._db = await aiosqlite.connect(self.db_path)
        await self._init_tables()

    async def disconnect(self):
        """断开连接"""
        if self._db:
            await self._db.close()
            self._db = None

    @asynccontextmanager
    async def get_cursor(self):
        """获取游标的上下文管理器"""
        if not self._db:
            await self.connect()
        cursor = await self._db.cursor()
        try:
            yield cursor
        finally:
            await cursor.close()

    async def _init_tables(self):
        """初始化数据表"""
        async with self.get_cursor() as cur:
            # 用户表
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    max_concurrent INTEGER DEFAULT 1,
                    monthly_quota INTEGER DEFAULT 1000000,
                    used_tokens INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    current_concurrent INTEGER DEFAULT 0
                )
            """)

            # 请求记录表
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    upstream_key_name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    latency_ms REAL DEFAULT 0,
                    status TEXT DEFAULT 'success',
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            await self._db.commit()

    # ============ 用户操作 ============

    async def create_user(self, user: User) -> User:
        """创建用户"""
        async with self.get_cursor() as cur:
            await cur.execute("""
                INSERT INTO users (id, name, api_key, created_at, max_concurrent, monthly_quota, used_tokens, is_active, current_concurrent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id, user.name, user.api_key, user.created_at.isoformat(),
                user.max_concurrent, user.monthly_quota, user.used_tokens,
                1 if user.is_active else 0, user.current_concurrent
            ))
            await self._db.commit()
        return user

    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """通过 API Key 获取用户"""
        async with self.get_cursor() as cur:
            await cur.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
            row = await cur.fetchone()
            if row:
                return self._row_to_user(row)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """通过 ID 获取用户"""
        async with self.get_cursor() as cur:
            await cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cur.fetchone()
            if row:
                return self._row_to_user(row)
        return None

    async def list_users(self) -> List[User]:
        """列出所有用户"""
        async with self.get_cursor() as cur:
            await cur.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = await cur.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def update_user_concurrent(self, user_id: str, delta: int):
        """更新用户并发数 (delta: +1 或 -1)"""
        async with self.get_cursor() as cur:
            await cur.execute("""
                UPDATE users SET current_concurrent = MAX(0, current_concurrent + ?)
                WHERE id = ?
            """, (delta, user_id))
            await self._db.commit()

    async def add_user_tokens(self, user_id: str, tokens: int):
        """增加用户已用 token 数"""
        async with self.get_cursor() as cur:
            await cur.execute("""
                UPDATE users SET used_tokens = used_tokens + ? WHERE id = ?
            """, (tokens, user_id))
            await self._db.commit()

    async def reset_monthly_usage(self):
        """重置月度用量（每月初调用）"""
        async with self.get_cursor() as cur:
            await cur.execute("UPDATE users SET used_tokens = 0")
            await self._db.commit()

    def _row_to_user(self, row) -> User:
        """数据库行转 User 对象"""
        return User(
            id=row[0],
            name=row[1],
            api_key=row[2],
            created_at=datetime.fromisoformat(row[3]),
            max_concurrent=row[4],
            monthly_quota=row[5],
            used_tokens=row[6],
            is_active=bool(row[7]),
            current_concurrent=row[8]
        )

    # ============ 请求记录 ============

    async def create_request(self, record: RequestRecord):
        """创建请求记录"""
        async with self.get_cursor() as cur:
            await cur.execute("""
                INSERT INTO requests (id, user_id, upstream_key_name, model, prompt_tokens, completion_tokens, created_at, latency_ms, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.user_id, record.upstream_key_name, record.model,
                record.prompt_tokens, record.completion_tokens,
                record.created_at.isoformat(), record.latency_ms, record.status
            ))
            await self._db.commit()

    async def get_user_stats(self, user_id: str) -> dict:
        """获取用户统计"""
        async with self.get_cursor() as cur:
            await cur.execute("""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(prompt_tokens) as total_prompt,
                    SUM(completion_tokens) as total_completion,
                    AVG(latency_ms) as avg_latency
                FROM requests WHERE user_id = ? AND status = 'success'
            """, (user_id,))
            row = await cur.fetchone()
            return {
                "total_requests": row[0] or 0,
                "total_prompt_tokens": row[1] or 0,
                "total_completion_tokens": row[2] or 0,
                "avg_latency_ms": row[3] or 0
            }


# 全局数据库实例
db = Database()
