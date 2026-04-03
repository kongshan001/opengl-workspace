#!/usr/bin/env python3
"""
Web 管理界面（美化版）
支持：终端、文件管理、系统监控、端口转发、用户管理
"""

import asyncio
import json
import os
import sys
import base64
import hashlib
from aiohttp import web
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import Config
from common.protocol import Message, MessageType, create_exec_message
from common.monitor import SystemMonitor
from common.tunnel import PortForwarder
from common.users import UserManager, Permission
from common.audit import audit_log, AuditEventType, get_audit_logger


class WebTerminal:
    """Web 终端会话"""
    
    def __init__(self, config: Config):
        self.config = config
        self.reader = None
        self.writer = None
        self.authenticated = False
    
    async def connect(self) -> bool:
        """连接到服务端"""
        try:
            host = self.config.server.host
            if host == "0.0.0.0":
                host = "127.0.0.1"
            
            self.reader, self.writer = await asyncio.open_connection(
                host, self.config.server.port
            )
            
            msg = Message(MessageType.AUTH, {"token": self.config.server.token})
            self.writer.write(msg.encode())
            await self.writer.drain()
            
            length_data = await self.reader.readexactly(4)
            length = int.from_bytes(length_data, 'big')
            data = await self.reader.readexactly(length)
            response = Message.decode(data)
            
            if response.type == MessageType.AUTH_OK:
                self.authenticated = True
                return True
            return False
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    async def execute(self, command: str) -> list:
        """执行命令"""
        if not self.authenticated:
            if not await self.connect():
                return [{"error": "无法连接到服务端"}]
        
        import uuid
        request_id = str(uuid.uuid4())[:8]
        
        await self._send(create_exec_message(command, request_id))
        
        outputs = []
        while True:
            try:
                msg = await self._recv()
                if msg.type == MessageType.OUTPUT:
                    outputs.append({
                        "text": msg.data.get("output", ""),
                        "stream": msg.data.get("stream", "stdout")
                    })
                elif msg.type == MessageType.EXIT:
                    outputs.append({"exit_code": msg.data.get("code", 0)})
                    break
                elif msg.type == MessageType.ERROR:
                    outputs.append({"error": msg.data.get("error", "")})
                    break
            except:
                break
        
        return outputs
    
    async def _send(self, msg: Message):
        self.writer.write(msg.encode())
        await self.writer.drain()
    
    async def _recv(self) -> Message:
        length_data = await self.reader.readexactly(4)
        length = int.from_bytes(length_data, 'big')
        data = await self.reader.readexactly(length)
        return Message.decode(data)
    
    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()


class WebServer:
    """Web 管理服务器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.user_manager = UserManager()
        self.app = web.Application(client_max_size=100 * 1024 * 1024)
        
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_post('/api/login', self.handle_login)
        self.app.router.add_post('/api/exec', self.handle_exec)
        self.app.router.add_post('/api/file/list', self.handle_file_list)
        self.app.router.add_get('/api/file/download', self.handle_file_download)
        self.app.router.add_post('/api/file/upload', self.handle_file_upload)
        self.app.router.add_get('/api/system/info', self.handle_system_info)
        self.app.router.add_get('/api/tunnel/list', self.handle_tunnel_list)
        self.app.router.add_post('/api/tunnel/create', self.handle_tunnel_create)
        self.app.router.add_post('/api/tunnel/remove', self.handle_tunnel_remove)
        self.app.router.add_get('/api/user/list', self.handle_user_list)
        self.app.router.add_post('/api/user/create', self.handle_user_create)
        self.app.router.add_post('/api/user/delete', self.handle_user_delete)
        self.app.router.add_post('/api/user/password', self.handle_user_password)
        self.app.router.add_get('/api/audit/list', self.handle_audit_list)
        self.app.router.add_get('/api/audit/stats', self.handle_audit_stats)
        self.app.router.add_get('/ws', self.handle_websocket)
    
    def _check_auth(self, request) -> tuple:
        """验证 Token"""
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return False, "未登录"
        
        token = auth[7:]
        return self.user_manager.verify_token(token)
    
    def _check_permission(self, request, permission: str) -> tuple:
        """检查权限"""
        is_valid, result = self._check_auth(request)
        if not is_valid:
            return False, result
        
        username = result
        if not self.user_manager.has_permission(username, permission):
            return False, "权限不足"
        
        return True, username
    
    async def handle_index(self, request):
        """主页"""
        html = self._get_index_html()
        return web.Response(text=html, content_type='text/html')
    
    async def handle_login(self, request):
        """登录"""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            
            success, token = self.user_manager.login(username, password)
            
            if success:
                audit_log(
                    AuditEventType.LOGIN_SUCCESS,
                    username=username,
                    ip_address=request.remote or "unknown",
                    description=f"用户登录: {username}"
                )
                permissions = self.user_manager.get_permissions(username)
                return web.json_response({
                    "success": True,
                    "token": token,
                    "permissions": permissions
                })
            else:
                audit_log(
                    AuditEventType.LOGIN_FAILED,
                    username=username,
                    ip_address=request.remote or "unknown",
                    description=f"登录失败: {username}",
                    success=False
                )
                return web.json_response({"error": "用户名或密码错误"}, status=401)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_exec(self, request):
        """执行命令"""
        is_valid, username = self._check_auth(request)
        if not is_valid:
            return web.json_response({"error": username}, status=401)
        
        try:
            data = await request.json()
            command = data.get('command', '')
            
            if not self.user_manager.has_permission(username, Permission.EXEC.value):
                return web.json_response({"error": "无执行权限"}, status=403)
            
            terminal = WebTerminal(self.config)
            outputs = await terminal.execute(command)
            await terminal.close()
            
            audit_log(
                AuditEventType.COMMAND_EXEC,
                username=username,
                ip_address=request.remote or "unknown",
                description=f"执行命令: {command}",
                details={"command": command}
            )
            
            return web.json_response({"outputs": outputs})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_file_list(self, request):
        """文件列表"""
        is_valid, result = self._check_permission(request, Permission.FILE_READ.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            data = await request.json()
            path = data.get('path', '/')
            
            terminal = WebTerminal(self.config)
            
            # 获取文件列表
            outputs = await terminal.execute(f'ls -lah "{path}" | tail -n +2')
            
            files = []
            if outputs and outputs[0].get('text'):
                lines = outputs[0]['text'].strip().split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 9:
                        is_dir = line.startswith('d')
                        name = ' '.join(parts[8:])
                        if name not in ['.', '..']:
                            files.append({
                                'name': name,
                                'path': os.path.join(path, name),
                                'type': 'directory' if is_dir else 'file',
                                'size': parts[4],
                                'perms': parts[0],
                                'owner': parts[2],
                                'modified': ' '.join(parts[5:8])
                            })
            
            await terminal.close()
            
            audit_log(
                AuditEventType.FILE_LIST,
                username=result,
                ip_address=request.remote or "unknown",
                description=f"浏览目录: {path}",
                details={"path": path}
            )
            
            return web.json_response({"files": files})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_file_download(self, request):
        """文件下载"""
        is_valid, result = self._check_permission(request, Permission.FILE_READ.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            path = request.query.get('path')
            
            audit_log(
                AuditEventType.FILE_DOWNLOAD,
                username=result,
                ip_address=request.remote or "unknown",
                description=f"下载文件: {path}",
                details={"path": path}
            )
            
            return web.FileResponse(path)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_file_upload(self, request):
        """文件上传"""
        is_valid, result = self._check_permission(request, Permission.FILE_WRITE.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            reader = await request.multipart()
            
            path = None
            file_data = None
            filename = None
            
            async for field in reader:
                if field.name == 'path':
                    path = await field.text()
                elif field.name == 'file':
                    filename = field.filename
                    file_data = await field.read()
            
            if path and file_data:
                filepath = os.path.join(path, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                
                audit_log(
                    AuditEventType.FILE_UPLOAD,
                    username=result,
                    ip_address=request.remote or "unknown",
                    description=f"上传文件: {filepath}",
                    details={"path": filepath, "size": len(file_data)}
                )
                
                return web.json_response({"success": True})
            
            return web.json_response({"error": "参数错误"}, status=400)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_system_info(self, request):
        """系统信息"""
        is_valid, result = self._check_auth(request)
        if not is_valid:
            return web.json_response({"error": result}, status=401)
        
        try:
            monitor = SystemMonitor()
            info = monitor.get_all_info()
            return web.json_response(info)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_tunnel_list(self, request):
        """隧道列表"""
        is_valid, result = self._check_permission(request, Permission.TUNNEL.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            tunnels = PortForwarder.list_tunnels()
            return web.json_response({"tunnels": tunnels})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_tunnel_create(self, request):
        """创建隧道"""
        is_valid, username = self._check_permission(request, Permission.TUNNEL.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            data = await request.json()
            listen_port = data.get('listen_port')
            target_host = data.get('target_host')
            target_port = data.get('target_port')
            
            success = await PortForwarder.create_tunnel(
                listen_port, target_host, target_port
            )
            
            if success:
                audit_log(
                    AuditEventType.TUNNEL_CREATE,
                    username=username,
                    ip_address=request.remote or "unknown",
                    description=f"创建隧道: {listen_port} -> {target_host}:{target_port}",
                    details={
                        "listen_port": listen_port,
                        "target": f"{target_host}:{target_port}"
                    }
                )
                return web.json_response({"success": True})
            else:
                return web.json_response({"error": "创建失败"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_tunnel_remove(self, request):
        """删除隧道"""
        is_valid, username = self._check_permission(request, Permission.TUNNEL.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            data = await request.json()
            listen_port = data.get('listen_port')
            
            success = await PortForwarder.remove_tunnel(listen_port)
            
            audit_log(
                AuditEventType.TUNNEL_REMOVE,
                username=username,
                ip_address=request.remote or "unknown",
                description=f"删除隧道: {listen_port}",
                details={"listen_port": listen_port},
                success=success
            )
            
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_user_list(self, request):
        """用户列表"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            users = self.user_manager.list_users()
            return web.json_response({"users": users})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_user_create(self, request):
        """创建用户"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            permissions = data.get('permissions', [])
            
            success = self.user_manager.create_user(username, password, permissions)
            
            audit_log(
                AuditEventType.USER_CREATE,
                username=result,  # 操作者
                ip_address=request.remote or "unknown",
                description=f"创建用户: {username}",
                details={"new_user": username, "permissions": permissions},
                success=success
            )
            
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_user_delete(self, request):
        """删除用户"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            data = await request.json()
            username = data.get('username')
            
            success = self.user_manager.delete_user(username)
            audit_log(
                AuditEventType.USER_DELETE,
                username=result,  # 操作者
                ip_address=request.remote or "unknown",
                description=f"删除用户: {username}",
                details={"deleted_user": username},
                success=success
            )
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_user_password(self, request):
        """修改密码"""
        is_valid, username = self._check_auth(request)
        if not is_valid:
            return web.json_response({"error": username}, status=401)
        
        try:
            data = await request.json()
            new_password = data.get('new_password')
            
            success = self.user_manager.update_password(username, new_password)
            audit_log(
                AuditEventType.USER_PASSWORD_CHANGE,
                username=username,
                ip_address=request.remote or "unknown",
                description="修改密码",
                success=success
            )
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_websocket(self, request):
        """WebSocket 终端"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        terminal = WebTerminal(self.config)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get('type') == 'exec':
                            command = data.get('command', '')
                            outputs = await terminal.execute(command)
                            await ws.send_json({"type": "result", "outputs": outputs})
                    except Exception as e:
                        await ws.send_json({"error": str(e)})
        finally:
            await terminal.close()
        
        return ws
    
    async def handle_audit_list(self, request):
        """审计日志列表"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            logger = get_audit_logger()
            
            # 解析查询参数
            event_type = request.query.get('event_type')
            username = request.query.get('username')
            ip_address = request.query.get('ip_address')
            success_str = request.query.get('success')
            hours_str = request.query.get('hours', '24')
            limit_str = request.query.get('limit', '100')
            offset_str = request.query.get('offset', '0')
            
            success = None
            if success_str and success_str.lower() in ('true', '1', 'yes'):
                success = True
            elif success_str and success_str.lower() in ('false', '0', 'no'):
                success = False
            
            hours = int(hours_str)
            limit = int(limit_str)
            offset = int(offset_str)
            
            import time
            start_time = time.time() - hours * 3600
            
            logs = logger.query(
                event_type=event_type,
                username=username,
                ip_address=ip_address,
                success=success,
                start_time=start_time,
                limit=limit,
                offset=offset
            )
            
            return web.json_response({"logs": logs, "count": len(logs)})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_audit_stats(self, request):
        """审计统计"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            logger = get_audit_logger()
            hours_str = request.query.get('hours', '24')
            hours = int(hours_str)
            
            stats = logger.get_stats(hours=hours)
            return web.json_response(stats)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    def _get_index_html(self) -> str:
        """返回主页 HTML（美化版）"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Remote Shell v2.0 - 优雅版</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* ===== 全局样式 ===== */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        :root {
            --primary: #6366f1;
            --primary-hover: #5558e3;
            --primary-light: #818cf8;
            --secondary: #8b5cf6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #3b82f6;
            
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-hover: #334155;
            --bg-input: #0f172a;
            
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            
            --border: #334155;
            --border-light: #475569;
            
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, #1a1f2e 100%);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* ===== 登录界面 ===== */
        .login-box {
            max-width: 440px;
            margin: 80px auto;
            background: var(--bg-card);
            padding: 48px;
            border-radius: 16px;
            box-shadow: var(--shadow-xl);
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }
        
        .login-box::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
        }
        
        .login-box h1 {
            text-align: center;
            margin-bottom: 12px;
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-light), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .login-box .subtitle {
            text-align: center;
            color: var(--text-secondary);
            margin-bottom: 32px;
            font-size: 14px;
        }
        
        .login-box input {
            width: 100%;
            padding: 14px 16px;
            margin: 8px 0;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-input);
            color: var(--text-primary);
            font-size: 15px;
            transition: all 0.2s ease;
        }
        
        .login-box input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        
        .login-box input::placeholder {
            color: var(--text-muted);
        }
        
        .login-box button {
            width: 100%;
            padding: 14px;
            margin-top: 24px;
            border: none;
            border-radius: 8px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-md);
        }
        
        .login-box button:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-lg);
        }
        
        .login-box button:active {
            transform: translateY(0);
        }
        
        /* ===== 主应用 ===== */
        .main-app {
            display: none;
        }
        
        /* ===== 头部 ===== */
        .header {
            background: var(--bg-card);
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }
        
        .header h1 {
            font-size: 22px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-light), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header-info {
            color: var(--text-secondary);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .header-info .status-dot {
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .header button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            background: var(--danger);
            color: white;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .header button:hover {
            background: #dc2626;
            transform: translateY(-1px);
        }
        
        /* ===== 标签页 ===== */
        .tabs {
            display: flex;
            background: var(--bg-card);
            padding: 0 24px;
            border-bottom: 1px solid var(--border);
            overflow-x: auto;
            gap: 4px;
        }
        
        .tab {
            padding: 14px 24px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            color: var(--text-secondary);
            white-space: nowrap;
            font-weight: 500;
            transition: all 0.2s ease;
            position: relative;
        }
        
        .tab:hover {
            color: var(--text-primary);
            background: rgba(99, 102, 241, 0.05);
        }
        
        .tab.active {
            color: var(--primary-light);
            border-bottom-color: var(--primary);
            background: rgba(99, 102, 241, 0.1);
        }
        
        .tab-content {
            padding: 24px;
            display: none;
            animation: fadeIn 0.3s ease;
        }
        
        .tab-content.active {
            display: block;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* ===== 终端 ===== */
        .terminal {
            background: var(--bg-dark);
            border-radius: 12px;
            padding: 20px;
            font-family: "SF Mono", "Monaco", "Menlo", "Consolas", monospace;
            font-size: 14px;
            height: calc(100vh - 260px);
            overflow-y: auto;
            margin-bottom: 16px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
        }
        
        .terminal::-webkit-scrollbar {
            width: 8px;
        }
        
        .terminal::-webkit-scrollbar-track {
            background: var(--bg-dark);
        }
        
        .terminal::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        
        .terminal::-webkit-scrollbar-thumb:hover {
            background: var(--border-light);
        }
        
        .terminal .line {
            white-space: pre-wrap;
            word-break: break-all;
            padding: 2px 0;
        }
        
        .terminal .stdout {
            color: var(--text-primary);
        }
        
        .terminal .stderr {
            color: var(--danger);
        }
        
        .terminal .prompt {
            color: var(--success);
            font-weight: 500;
        }
        
        .command-input {
            display: flex;
            gap: 12px;
        }
        
        .command-input input {
            flex: 1;
            padding: 14px 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-input);
            color: var(--text-primary);
            font-family: "SF Mono", "Monaco", monospace;
            font-size: 14px;
            transition: all 0.2s ease;
        }
        
        .command-input input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        
        .command-input button {
            padding: 14px 32px;
            border: none;
            border-radius: 8px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-md);
        }
        
        .command-input button:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-lg);
        }
        
        /* ===== 文件管理 ===== */
        .path-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
        }
        
        .path-bar input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-card);
            color: var(--text-primary);
            font-size: 14px;
            transition: all 0.2s ease;
        }
        
        .path-bar input:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .path-bar button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .path-bar button.primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
        }
        
        .path-bar button.secondary {
            background: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }
        
        .path-bar button:hover {
            transform: translateY(-1px);
        }
        
        .file-list {
            background: var(--bg-card);
            border-radius: 12px;
            max-height: calc(100vh - 260px);
            overflow-y: auto;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
        }
        
        .file-item {
            display: flex;
            align-items: center;
            padding: 14px 20px;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .file-item:last-child {
            border-bottom: none;
        }
        
        .file-item:hover {
            background: var(--bg-hover);
        }
        
        .file-icon {
            margin-right: 12px;
            font-size: 24px;
        }
        
        .file-name {
            flex: 1;
            font-weight: 500;
        }
        
        .file-size {
            color: var(--text-secondary);
            margin-right: 20px;
            font-size: 13px;
        }
        
        /* ===== 系统监控 ===== */
        .monitor-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }
        
        .monitor-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
            transition: all 0.2s ease;
        }
        
        .monitor-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }
        
        .monitor-card h3 {
            color: var(--primary-light);
            margin-bottom: 16px;
            font-size: 18px;
            font-weight: 600;
        }
        
        .monitor-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }
        
        .monitor-row:last-child {
            border-bottom: none;
        }
        
        .monitor-row span:first-child {
            color: var(--text-secondary);
        }
        
        .monitor-row span:last-child {
            color: var(--text-primary);
            font-weight: 500;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--bg-dark);
            border-radius: 4px;
            margin-top: 8px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        .progress-fill.warning {
            background: linear-gradient(90deg, var(--warning), #fb923c);
        }
        
        .progress-fill.danger {
            background: linear-gradient(90deg, var(--danger), #f87171);
        }
        
        /* ===== 隧道管理 ===== */
        .tunnel-form, .user-form {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
        }
        
        .tunnel-form h3, .user-form h3 {
            color: var(--primary-light);
            margin-bottom: 16px;
            font-size: 18px;
            font-weight: 600;
        }
        
        .tunnel-form input, .user-form input {
            padding: 12px 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-input);
            color: var(--text-primary);
            margin-right: 12px;
            width: 140px;
            font-size: 14px;
            transition: all 0.2s ease;
        }
        
        .tunnel-form input:focus, .user-form input:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .tunnel-form button, .user-form button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-md);
        }
        
        .tunnel-form button:hover, .user-form button:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-lg);
        }
        
        .tunnel-list, .user-list {
            background: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
        }
        
        .tunnel-item, .user-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
        }
        
        .tunnel-item:last-child, .user-item:last-child {
            border-bottom: none;
        }
        
        .tunnel-item button, .user-item button {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            background: var(--danger);
            color: white;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .tunnel-item button:hover, .user-item button:hover {
            background: #dc2626;
        }
        
        .user-permissions {
            color: var(--text-secondary);
            font-size: 12px;
            margin-top: 4px;
        }
        
        /* ===== 审计日志 ===== */
        .audit-stats {
            margin-bottom: 20px;
        }
        
        .audit-filters {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
        }
        
        .audit-filters select, .audit-filters input {
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-input);
            color: var(--text-primary);
            font-size: 14px;
            transition: all 0.2s ease;
        }
        
        .audit-filters select:focus, .audit-filters input:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .audit-filters button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-md);
        }
        
        .audit-filters button:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-lg);
        }
        
        .audit-list {
            background: var(--bg-card);
            border-radius: 12px;
            max-height: calc(100vh - 400px);
            overflow-y: auto;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
        }
        
        .audit-item {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            transition: all 0.2s ease;
        }
        
        .audit-item:hover {
            background: var(--bg-hover);
        }
        
        .audit-item:last-child {
            border-bottom: none;
        }
        
        /* ===== 统计卡片 ===== */
        .stat-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid var(--border);
            transition: all 0.2s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        .stat-card .value {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-light), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .stat-card .label {
            color: var(--text-secondary);
            font-size: 13px;
            margin-top: 4px;
        }
        
        /* ===== 错误提示 ===== */
        .error {
            color: var(--danger);
            text-align: center;
            margin-top: 16px;
            font-size: 14px;
        }
        
        /* ===== 响应式 ===== */
        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                gap: 12px;
            }
            
            .monitor-grid {
                grid-template-columns: 1fr;
            }
            
            .tunnel-form input, .user-form input {
                width: 100%;
                margin-bottom: 12px;
            }
        }
    </style>
</head>
<body>
    <div class="login-box" id="loginBox">
        <h1>🔺 Remote Shell</h1>
        <div class="subtitle">远程服务器管理系统</div>
        <input type="text" id="username" placeholder="用户名" value="admin">
        <input type="password" id="password" placeholder="密码">
        <button onclick="login()">登录</button>
        <p id="loginError" class="error"></p>
    </div>
    
    <div class="main-app" id="mainApp">
        <div class="header">
            <h1>🔺 Remote Shell</h1>
            <div class="header-info">
                <span class="status-dot"></span>
                <span id="serverInfo">连接中...</span>
            </div>
            <button onclick="logout()">退出登录</button>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('terminal')">💻 终端</div>
            <div class="tab" onclick="showTab('files')">📁 文件</div>
            <div class="tab" onclick="showTab('monitor')">📊 监控</div>
            <div class="tab" onclick="showTab('tunnel')">🔗 隧道</div>
            <div class="tab" onclick="showTab('users')">👥 用户</div>
            <div class="tab" onclick="showTab('audit')">📋 审计</div>
        </div>
        
        <!-- 终端 -->
        <div class="tab-content active" id="terminalTab">
            <div class="terminal" id="terminal"></div>
            <div class="command-input">
                <input type="text" id="cmdInput" placeholder="输入命令..." onkeypress="if(event.key==='Enter')execute()">
                <button onclick="execute()">执行</button>
            </div>
        </div>
        
        <!-- 文件管理 -->
        <div class="tab-content" id="filesTab">
            <div class="path-bar">
                <input type="text" id="filePath" placeholder="路径" value="/">
                <button class="primary" onclick="listFiles()">浏览</button>
                <button class="secondary" onclick="uploadFile()">上传文件</button>
            </div>
            <div class="file-list" id="fileList"></div>
        </div>
        
        <!-- 系统监控 -->
        <div class="tab-content" id="monitorTab">
            <div class="monitor-grid" id="monitorGrid"></div>
        </div>
        
        <!-- 端口转发 -->
        <div class="tab-content" id="tunnelTab">
            <div class="tunnel-form">
                <h3>创建隧道</h3>
                <input type="number" id="tunnelListen" placeholder="监听端口">
                <input type="text" id="tunnelHost" placeholder="目标主机">
                <input type="number" id="tunnelPort" placeholder="目标端口">
                <button onclick="createTunnel()">创建</button>
            </div>
            <div class="tunnel-list" id="tunnelList"></div>
        </div>
        
        <!-- 用户管理 -->
        <div class="tab-content" id="usersTab">
            <div class="user-form">
                <h3>创建用户</h3>
                <input type="text" id="newUsername" placeholder="用户名">
                <input type="password" id="newPassword" placeholder="密码">
                <button onclick="createUser()">创建</button>
            </div>
            <div class="user-list" id="userList"></div>
        </div>
        
        <!-- 审计日志 -->
        <div class="tab-content" id="auditTab">
            <div class="audit-stats" id="auditStats"></div>
            <div class="audit-filters">
                <select id="auditType">
                    <option value="">全部类型</option>
                    <option value="login_success">登录成功</option>
                    <option value="login_failed">登录失败</option>
                    <option value="command_exec">命令执行</option>
                    <option value="command_success">命令成功</option>
                    <option value="command_failed">命令失败</option>
                    <option value="file_download">文件下载</option>
                    <option value="file_upload">文件上传</option>
                    <option value="tunnel_create">隧道创建</option>
                    <option value="tunnel_remove">隧道删除</option>
                    <option value="user_create">用户创建</option>
                    <option value="user_delete">用户删除</option>
                </select>
                <input type="text" id="auditUser" placeholder="用户名">
                <input type="text" id="auditIP" placeholder="IP 地址">
                <select id="auditHours">
                    <option value="24">最近 24 小时</option>
                    <option value="72">最近 3 天</option>
                    <option value="168">最近 7 天</option>
                    <option value="720">最近 30 天</option>
                </select>
                <button onclick="loadAuditLogs()">查询</button>
            </div>
            <div class="audit-list" id="auditList"></div>
        </div>
    </div>
    
    <script>
        let token = '';
        let permissions = [];
        
        async function api(path, method = 'GET', data = null) {
            const opts = {
                method,
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
            };
            if (data) opts.body = JSON.stringify(data);
            const res = await fetch(path, opts);
            return res.json();
        }
        
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await res.json();
                if (data.success) {
                    token = data.token;
                    permissions = data.permissions || [];
                    document.getElementById('loginBox').style.display = 'none';
                    document.getElementById('mainApp').style.display = 'block';
                    loadMonitor();
                    listFiles('/');
                } else {
                    document.getElementById('loginError').textContent = data.error;
                }
            } catch (e) {
                document.getElementById('loginError').textContent = '连接失败';
            }
        }
        
        function logout() {
            token = '';
            document.getElementById('loginBox').style.display = 'block';
            document.getElementById('mainApp').style.display = 'none';
        }
        
        function showTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(name + 'Tab').classList.add('active');
            if (name === 'monitor') loadMonitor();
            if (name === 'tunnel') listTunnels();
            if (name === 'users') listUsers();
            if (name === 'audit') loadAuditLogs();
        }
        
        async function execute() {
            const cmd = document.getElementById('cmdInput').value;
            if (!cmd) return;
            const terminal = document.getElementById('terminal');
            terminal.innerHTML += '<div class="line prompt">$ ' + cmd + '</div>';
            document.getElementById('cmdInput').value = '';
            
            try {
                const data = await api('/api/exec', 'POST', {command: cmd});
                if (data.outputs) {
                    data.outputs.forEach(o => {
                        if (o.text) terminal.innerHTML += '<div class="line ' + (o.stream || 'stdout') + '">' + escapeHtml(o.text) + '</div>';
                    });
                }
                if (data.error) terminal.innerHTML += '<div class="line stderr">错误: ' + data.error + '</div>';
            } catch (e) {
                terminal.innerHTML += '<div class="line stderr">请求失败: ' + e + '</div>';
            }
            terminal.scrollTop = terminal.scrollHeight;
        }
        
        async function listFiles(path) {
            if (!path) path = document.getElementById('filePath').value;
            try {
                const data = await api('/api/file/list', 'POST', {path});
                const list = document.getElementById('fileList');
                list.innerHTML = '';
                if (data.files) {
                    data.files.forEach(f => {
                        const icon = f.type === 'directory' ? '📁' : '📄';
                        list.innerHTML += `<div class="file-item" onclick="${f.type === 'directory' ? `listFiles('${f.path}')` : `downloadFile('${f.path}')`}">
                            <span class="file-icon">${icon}</span>
                            <span class="file-name">${f.name}</span>
                            <span class="file-size">${formatSize(f.size)}</span>
                        </div>`;
                    });
                }
                document.getElementById('filePath').value = path;
            } catch (e) { alert('获取文件列表失败'); }
        }
        
        function downloadFile(path) { window.open('/api/file/download?path=' + encodeURIComponent(path) + '&token=' + token); }
        
        function uploadFile() {
            const input = document.createElement('input');
            input.type = 'file';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                const path = document.getElementById('filePath').value;
                const formData = new FormData();
                formData.append('file', file);
                formData.append('path', path);
                try {
                    const res = await fetch('/api/file/upload', {method: 'POST', headers: {'Authorization': 'Bearer ' + token}, body: formData});
                    const data = await res.json();
                    if (data.success) listFiles(path);
                    else alert(data.error);
                } catch (e) { alert('上传失败'); }
            };
            input.click();
        }
        
        async function loadMonitor() {
            try {
                const data = await api('/api/system/info');
                const grid = document.getElementById('monitorGrid');
                const pctClass = (p) => p > 80 ? 'danger' : p > 60 ? 'warning' : '';
                grid.innerHTML = `
                    <div class="monitor-card">
                        <h3>💻 系统信息</h3>
                        <div class="monitor-row"><span>主机名</span><span>${data.hostname}</span></div>
                        <div class="monitor-row"><span>时间</span><span>${data.time}</span></div>
                        <div class="monitor-row"><span>运行时间</span><span>${data.uptime_days} 天</span></div>
                    </div>
                    <div class="monitor-card">
                        <h3>🖥️ CPU 使用率</h3>
                        <div class="monitor-row"><span>当前使用率</span><span>${data.cpu.usage}%</span></div>
                        <div class="progress-bar"><div class="progress-fill ${pctClass(data.cpu.usage)}" style="width:${data.cpu.usage}%"></div></div>
                        <div class="monitor-row"><span>核心数</span><span>${data.cpu.cores}</span></div>
                        <div class="monitor-row"><span>负载</span><span>${data.cpu.load_avg.join(' / ')}</span></div>
                    </div>
                    <div class="monitor-card">
                        <h3>🧠 内存使用</h3>
                        <div class="monitor-row"><span>使用率</span><span>${data.memory.percent}%</span></div>
                        <div class="progress-bar"><div class="progress-fill ${pctClass(data.memory.percent)}" style="width:${data.memory.percent}%"></div></div>
                        <div class="monitor-row"><span>已用</span><span>${formatSize(data.memory.used)}</span></div>
                        <div class="monitor-row"><span>总计</span><span>${formatSize(data.memory.total)}</span></div>
                    </div>
                    ${data.disks.map(d => `
                    <div class="monitor-card">
                        <h3>💾 ${d.mount}</h3>
                        <div class="monitor-row"><span>使用率</span><span>${d.percent}%</span></div>
                        <div class="progress-bar"><div class="progress-fill ${pctClass(d.percent)}" style="width:${d.percent}%"></div></div>
                        <div class="monitor-row"><span>已用</span><span>${formatSize(d.used)}</span></div>
                        <div class="monitor-row"><span>总计</span><span>${formatSize(d.total)}</span></div>
                    </div>
                    `).join('')}
                `;
                document.getElementById('serverInfo').innerHTML = `<span class="status-dot"></span>${data.hostname} | CPU: ${data.cpu.usage}% | 内存: ${data.memory.percent}%`;
            } catch (e) {}
        }
        
        async function listTunnels() {
            try {
                const data = await api('/api/tunnel/list');
                const list = document.getElementById('tunnelList');
                list.innerHTML = '<h3 style="color:#818cf8;padding:20px;font-weight:600;">活跃隧道</h3>';
                if (data.tunnels && data.tunnels.length) {
                    data.tunnels.forEach(t => {
                        list.innerHTML += `<div class="tunnel-item">
                            <span>端口 ${t.listen_port} → ${t.target}</span>
                            <span>连接: ${t.connections} | ↑${formatSize(t.bytes_out)} ↓${formatSize(t.bytes_in)}</span>
                            <button onclick="removeTunnel(${t.listen_port})">删除</button>
                        </div>`;
                    });
                } else {
                    list.innerHTML += '<div style="padding:40px;color:#94a3b8;text-align:center;">暂无隧道</div>';
                }
            } catch (e) {}
        }
        
        async function createTunnel() {
            const listen = document.getElementById('tunnelListen').value;
            const host = document.getElementById('tunnelHost').value;
            const port = document.getElementById('tunnelPort').value;
            if (!listen || !host || !port) return alert('请填写完整');
            try {
                const data = await api('/api/tunnel/create', 'POST', {listen_port: parseInt(listen), target_host: host, target_port: parseInt(port)});
                if (data.success) { listTunnels(); alert('隧道已创建'); }
                else alert(data.error);
            } catch (e) { alert('创建失败'); }
        }
        
        async function removeTunnel(port) {
            try {
                await api('/api/tunnel/remove', 'POST', {listen_port: port});
                listTunnels();
            } catch (e) {}
        }
        
        async function listUsers() {
            try {
                const data = await api('/api/user/list');
                const list = document.getElementById('userList');
                list.innerHTML = '';
                if (data.users) {
                    data.users.forEach(u => {
                        list.innerHTML += `<div class="user-item">
                            <div><strong>${u.username}</strong><div class="user-permissions">${u.permissions.join(', ')}</div></div>
                            <button onclick="deleteUser('${u.username}')" ${u.username === 'admin' ? 'disabled' : ''}>删除</button>
                        </div>`;
                    });
                }
            } catch (e) {}
        }
        
        async function createUser() {
            const username = document.getElementById('newUsername').value;
            const password = document.getElementById('newPassword').value;
            if (!username || !password) return alert('请填写完整');
            try {
                const data = await api('/api/user/create', 'POST', {username, password, permissions: ['exec', 'file_read']});
                if (data.success) { listUsers(); alert('用户已创建'); }
                else alert(data.error);
            } catch (e) { alert('创建失败'); }
        }
        
        async function deleteUser(username) {
            if (!confirm('确定删除用户 ' + username + '?')) return;
            try {
                await api('/api/user/delete', 'POST', {username});
                listUsers();
            } catch (e) {}
        }
        
        function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }
        function formatSize(bytes) { if (!bytes) return '0 B'; const k = 1024; const s = ['B', 'KB', 'MB', 'GB']; const i = Math.floor(Math.log(bytes) / Math.log(k)); return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + s[i]; }
        
        // 审计日志
        async function loadAuditLogs() {
            try {
                const type = document.getElementById('auditType').value;
                const user = document.getElementById('auditUser').value;
                const ip = document.getElementById('auditIP').value;
                const hours = document.getElementById('auditHours').value;
                
                let url = `/api/audit/list?hours=${hours}&limit=200`;
                if (type) url += `&event_type=${type}`;
                if (user) url += `&username=${encodeURIComponent(user)}`;
                if (ip) url += `&ip_address=${encodeURIComponent(ip)}`;
                
                const data = await api(url);
                const list = document.getElementById('auditList');
                
                if (data.logs && data.logs.length) {
                    list.innerHTML = data.logs.map(log => `
                        <div class="audit-item">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                                <span style="font-weight:600;color:${log.success ? '#10b981' : '#ef4444'};">
                                    ${log.success ? '✓' : '✗'} ${log.event_type}
                                </span>
                                <span style="color:#94a3b8;font-size:12px;">${log.datetime}</span>
                            </div>
                            <div style="color:#f1f5f9;margin-bottom:6px;">${escapeHtml(log.description)}</div>
                            <div style="color:#94a3b8;font-size:12px;">
                                ${log.username ? `用户: ${log.username}` : ''} 
                                ${log.ip_address ? `| IP: ${log.ip_address}` : ''}
                            </div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div style="padding:40px;color:#94a3b8;text-align:center;">暂无审计日志</div>';
                }
                
                // 同时加载统计
                loadAuditStats(hours);
            } catch (e) {
                console.error('加载审计日志失败:', e);
            }
        }
        
        async function loadAuditStats(hours) {
            try {
                const data = await api(`/api/audit/stats?hours=${hours || 24}`);
                const stats = document.getElementById('auditStats');
                
                stats.innerHTML = `
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;">
                        <div class="stat-card">
                            <div class="value">${data.total_events || 0}</div>
                            <div class="label">总事件</div>
                        </div>
                        <div class="stat-card">
                            <div class="value">${data.successful || 0}</div>
                            <div class="label">成功</div>
                        </div>
                        <div class="stat-card">
                            <div class="value" style="background:none;-webkit-text-fill-color:#ef4444;">${data.failed || 0}</div>
                            <div class="label">失败</div>
                        </div>
                        <div class="stat-card">
                            <div class="value">${data.unique_users || 0}</div>
                            <div class="label">活跃用户</div>
                        </div>
                        <div class="stat-card">
                            <div class="value">${data.unique_ips || 0}</div>
                            <div class="label">独立 IP</div>
                        </div>
                    </div>
                `;
            } catch (e) {
                console.error('加载审计统计失败:', e);
            }
        }
        
        document.getElementById('password').addEventListener('keypress', (e) => { if (e.key === 'Enter') login(); });
        setInterval(loadMonitor, 5000);
    </script>
</body>
</html>'''
    
    def run(self):
        """启动"""
        print(f"[Web] 启动管理界面: http://{self.config.web.host}:{self.config.web.port}")
        print(f"[Web] 用户名: {self.config.web.username}")
        print(f"[Web] 密码: {self.config.web.password}")
        
        web.run_app(self.app, host=self.config.web.host, port=self.config.web.port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/remote-shell/config.json")
    args = parser.parse_args()
    
    config = Config.load(args.config) if os.path.exists(args.config) else Config()
    WebServer(config).run()
