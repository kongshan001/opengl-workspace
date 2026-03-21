"""
AI Gateway CLI - 命令行管理工具
"""
import sys
import os
import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.storage import db
from core.models import User
from core.load_balancer import load_balancer

console = Console()


def async_command(f):
    """将异步函数转换为 Click 命令"""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# ============ 服务管理 ============

@click.group()
def cli():
    """AI Gateway - AI API 代理网关管理工具"""
    pass


@cli.command()
@click.option('--host', default='0.0.0.0', help='监听地址')
@click.option('--port', default=8765, help='监听端口')
def serve(host: str, port: int):
    """启动 API 服务器"""
    import uvicorn
    from api.server import app
    
    console.print(Panel.fit(
        f"[bold green]AI Gateway[/bold green] 启动中...\n"
        f"地址: http://{host}:{port}\n"
        f"文档: http://{host}:{port}/docs",
        title="🚀 AI Gateway"
    ))
    
    uvicorn.run(app, host=host, port=port)


# ============ 用户管理 ============

@cli.group()
def user():
    """用户管理"""
    pass


@user.command("create")
@click.argument('name')
@click.option('--concurrent', '-c', default=1, help='最大并发数')
@click.option('--quota', '-q', default=1000000, help='月度 token 配额')
@async_command
async def create_user(name: str, concurrent: int, quota: int):
    """创建新用户"""
    await db.connect()
    
    user = User.create(
        name=name,
        max_concurrent=concurrent,
        monthly_quota=quota
    )
    await db.create_user(user)
    
    console.print(Panel.fit(
        f"[bold]用户创建成功[/bold]\n\n"
        f"名称: {user.name}\n"
        f"API Key: [bold green]{user.api_key}[/bold green]\n"
        f"并发限制: {user.max_concurrent}\n"
        f"月度配额: {user.monthly_quota:,} tokens",
        title="✅ 创建用户"
    ))
    
    await db.disconnect()


@user.command("list")
@async_command
async def list_users():
    """列出所有用户"""
    await db.connect()
    users = await db.list_users()
    
    table = Table(title="用户列表")
    table.add_column("ID", style="dim")
    table.add_column("名称")
    table.add_column("API Key")
    table.add_column("并发", justify="right")
    table.add_column("配额", justify="right")
    table.add_column("已用", justify="right")
    table.add_column("状态")
    
    for u in users:
        status = "[green]活跃[/green]" if u.is_active else "[red]禁用[/red]"
        table.add_row(
            u.id[:8],
            u.name,
            u.api_key[:15] + "...",
            f"{u.current_concurrent}/{u.max_concurrent}",
            f"{u.monthly_quota:,}",
            f"{u.used_tokens:,}",
            status
        )
    
    console.print(table)
    await db.disconnect()


@user.command("stats")
@click.argument('user_id')
@async_command
async def user_stats(user_id: str):
    """查看用户统计"""
    await db.connect()
    
    user = await db.get_user_by_id(user_id)
    if not user:
        console.print("[red]用户不存在[/red]")
        return
    
    stats = await db.get_user_stats(user_id)
    
    console.print(Panel.fit(
        f"[bold]用户统计[/bold]\n\n"
        f"名称: {user.name}\n"
        f"API Key: {user.api_key}\n"
        f"总请求数: {stats['total_requests']}\n"
        f"Prompt Tokens: {stats['total_prompt_tokens']:,}\n"
        f"Completion Tokens: {stats['total_completion_tokens']:,}\n"
        f"平均延迟: {stats['avg_latency_ms']:.1f}ms\n"
        f"月度配额: {user.monthly_quota:,}\n"
        f"已用配额: {user.used_tokens:,} ({user.used_tokens/user.monthly_quota*100:.1f}%)",
        title=f"📊 {user.name}"
    ))
    
    await db.disconnect()


# ============ 上游 Key 管理 ============

@cli.group()
def upstream():
    """上游 Key 管理"""
    pass


@upstream.command("status")
@async_command
async def upstream_status():
    """查看上游 Key 状态"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    load_balancer.load_from_config(str(config_path))
    
    status = load_balancer.get_status()
    
    table = Table(title="上游 Key 状态")
    table.add_column("名称")
    table.add_column("Provider")
    table.add_column("并发", justify="right")
    table.add_column("状态")
    
    for name, info in status['keys'].items():
        concurrent = f"{info['current_concurrent']}/{info['max_concurrent']}"
        status_text = "[green]启用[/green]" if info['enabled'] else "[red]禁用[/red]"
        table.add_row(name, info['provider'], concurrent, status_text)
    
    console.print(table)
    console.print(f"\n策略: {status['strategy']}")
    console.print(f"总请求: {status['stats']['total_requests']} | "
                  f"成功: {status['stats']['successful']} | "
                  f"失败: {status['stats']['failed']}")


# ============ 配置管理 ============

@cli.group()
def config():
    """配置管理"""
    pass


@config.command("show")
def show_config():
    """显示当前配置"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    
    if config_path.exists():
        console.print(Panel.fit(
            config_path.read_text(),
            title=f"📄 {config_path}"
        ))
    else:
        console.print("[red]配置文件不存在[/red]")


@config.command("init")
def init_config():
    """初始化配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    
    if config_path.exists():
        console.print("[yellow]配置文件已存在，跳过初始化[/yellow]")
        return
    
    config_content = """# AI Gateway 配置文件

server:
  host: "0.0.0.0"
  port: 8765

# 上游 API Key 池
upstream_keys:
  - name: "joiner-1"
    provider: "joiner"
    api_key: "${JOINER_API_KEY}"  # 设置环境变量 JOINER_API_KEY
    base_url: "https://api.joiner.ai/v1"
    max_concurrent: 2
    enabled: true

# 用户限制
user_limits:
  max_concurrent: 1
  default_monthly_quota: 1000000

# 负载均衡策略
load_balance:
  strategy: "least_loaded"
"""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_content)
    
    console.print(f"[green]配置文件已创建: {config_path}[/green]")
    console.print("[yellow]请设置环境变量 JOINER_API_KEY 或直接修改配置文件[/yellow]")


# ============ 测试命令 ============

@cli.command()
@click.option('--api-key', required=True, help='用户 API Key')
@click.option('--model', default='gpt-3.5-turbo', help='模型名称')
@click.option('--message', default='Hello!', help='测试消息')
@async_command
async def test(api_key: str, model: str, message: str):
    """测试 API 调用"""
    import httpx
    
    url = "http://localhost:8765/chat/completions"
    
    console.print(f"[bold]测试请求[/bold]")
    console.print(f"URL: {url}")
    console.print(f"Model: {model}")
    console.print(f"Message: {message}")
    console.print()
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": message}]
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            console.print(Panel.fit(content, title="🤖 回复"))
        else:
            console.print(f"[red]错误: {response.status_code}[/red]")
            console.print(response.text)


if __name__ == "__main__":
    cli()
