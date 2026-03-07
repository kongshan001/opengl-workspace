#!/usr/bin/env python3
"""
Web 管理界面（增强版）
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
            try:
                await self.writer.wait_closed()
            except:
                pass


class WebServer:
    """Web 服务器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.app = web.Application()
        self.port_forwarder = PortForwarder()
        self.user_manager = UserManager()
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        # 静态页面
        self.app.router.add_get('/', self.handle_index)
        
        # API
        self.app.router.add_get('/api/info', self.handle_info)
        self.app.router.add_post('/api/login', self.handle_login)
        self.app.router.add_post('/api/logout', self.handle_logout)
        
        # 终端
        self.app.router.add_post('/api/exec', self.handle_exec)
        self.app.router.add_get('/ws', self.handle_websocket)
        
        # 文件
        self.app.router.add_post('/api/file/list', self.handle_file_list)
        self.app.router.add_get('/api/file/download', self.handle_file_download)
        self.app.router.add_post('/api/file/upload', self.handle_file_upload)
        
        # 系统监控
        self.app.router.add_get('/api/system/info', self.handle_system_info)
        self.app.router.add_get('/api/system/processes', self.handle_processes)
        
        # 端口转发
        self.app.router.add_get('/api/tunnel/list', self.handle_tunnel_list)
        self.app.router.add_post('/api/tunnel/create', self.handle_tunnel_create)
        self.app.router.add_post('/api/tunnel/remove', self.handle_tunnel_remove)
        
        # 用户管理
        self.app.router.add_get('/api/user/list', self.handle_user_list)
        self.app.router.add_post('/api/user/create', self.handle_user_create)
        self.app.router.add_post('/api/user/delete', self.handle_user_delete)
        self.app.router.add_post('/api/user/password', self.handle_user_password)
    
    def _check_auth(self, request) -> tuple:
        """检查认证，返回 (is_valid, username_or_error)"""
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth[7:]
            username = self.user_manager.validate_session(token)
            if username:
                return True, username
        return False, "未认证"
    
    def _check_permission(self, request, permission: str) -> tuple:
        """检查权限"""
        is_valid, username = self._check_auth(request)
        if not is_valid:
            return False, username
        
        user = self.user_manager.get_user(username)
        if user and user.has_permission(permission):
            return True, username
        
        return False, "权限不足"
    
    async def handle_index(self, request):
        """返回主页"""
        html = self._get_index_html()
        return web.Response(text=html, content_type='text/html')
    
    async def handle_info(self, request):
        """服务器信息"""
        return web.json_response({
            "name": "Remote Shell",
            "version": "2.0.0",
            "features": ["terminal", "files", "monitor", "tunnel", "users"]
        })
    
    async def handle_login(self, request):
        """登录"""
        try:
            data = await request.json()
            username = data.get('username', '')
            password = data.get('password', '')
            
            token = self.user_manager.authenticate(username, password)
            if token:
                user = self.user_manager.get_user(username)
                return web.json_response({
                    "success": True,
                    "token": token,
                    "permissions": user.permissions if user else []
                })
            else:
                return web.json_response({"success": False, "error": "用户名或密码错误"}, status=401)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)
    
    async def handle_logout(self, request):
        """登出"""
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            self.user_manager.logout(auth[7:])
        return web.json_response({"success": True})
    
    async def handle_exec(self, request):
        """执行命令"""
        is_valid, result = self._check_permission(request, Permission.EXEC.value)
        if not is_valid:
            return web.json_response({"error": result}, status=401 if result == "未认证" else 403)
        
        try:
            data = await request.json()
            command = data.get('command', '')
            
            terminal = WebTerminal(self.config)
            outputs = await terminal.execute(command)
            await terminal.close()
            
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
            path = data.get('path', '.')
            path = os.path.abspath(os.path.expanduser(path))
            
            files = []
            if os.path.exists(path):
                if os.path.isfile(path):
                    stat = os.stat(path)
                    files.append({
                        "name": os.path.basename(path),
                        "path": path,
                        "type": "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
                else:
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        try:
                            stat = os.stat(item_path)
                            files.append({
                                "name": item,
                                "path": item_path,
                                "type": "directory" if os.path.isdir(item_path) else "file",
                                "size": stat.st_size if os.path.isfile(item_path) else 0,
                                "modified": stat.st_mtime
                            })
                        except:
                            pass
            
            return web.json_response({"files": files, "path": path})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_file_download(self, request):
        """下载文件"""
        is_valid, result = self._check_permission(request, Permission.FILE_READ.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        path = request.query.get('path', '')
        if not path:
            return web.json_response({"error": "缺少路径"}, status=400)
        
        try:
            path = os.path.abspath(os.path.expanduser(path))
            if not os.path.isfile(path):
                return web.json_response({"error": "文件不存在"}, status=404)
            
            with open(path, 'rb') as f:
                content = f.read()
            
            return web.Response(
                body=content,
                headers={'Content-Disposition': f'attachment; filename="{os.path.basename(path)}"'}
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_file_upload(self, request):
        """上传文件"""
        is_valid, result = self._check_permission(request, Permission.FILE_WRITE.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            reader = await request.multipart()
            path, file_data, filename = "", b"", ""
            
            async for field in reader:
                if field.name == 'path':
                    path = await field.text()
                elif field.name == 'file':
                    filename = field.filename
                    file_data = await field.read()
            
            if not path or not file_data:
                return web.json_response({"error": "缺少文件或路径"}, status=400)
            
            path = os.path.abspath(os.path.expanduser(path))
            if os.path.isdir(path):
                path = os.path.join(path, filename)
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(file_data)
            
            return web.json_response({"success": True, "path": path})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_system_info(self, request):
        """系统信息"""
        is_valid, result = self._check_auth(request)
        if not is_valid:
            return web.json_response({"error": result}, status=401)
        
        try:
            info = await SystemMonitor.get_system_info()
            return web.json_response(info)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_processes(self, request):
        """进程列表"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            processes = await SystemMonitor.get_processes(limit=50)
            return web.json_response({
                "processes": [
                    {"pid": p.pid, "name": p.name, "status": p.status, "command": p.command}
                    for p in processes
                ]
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_tunnel_list(self, request):
        """隧道列表"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        return web.json_response({"tunnels": self.port_forwarder.list_tunnels()})
    
    async def handle_tunnel_create(self, request):
        """创建隧道"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            data = await request.json()
            listen_port = data.get('listen_port')
            target_host = data.get('target_host')
            target_port = data.get('target_port')
            
            if not all([listen_port, target_host, target_port]):
                return web.json_response({"error": "参数不完整"}, status=400)
            
            tunnel_id = await self.port_forwarder.create_tunnel(
                int(listen_port), target_host, int(target_port)
            )
            return web.json_response({"success": True, "tunnel_id": tunnel_id})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_tunnel_remove(self, request):
        """移除隧道"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            data = await request.json()
            listen_port = data.get('listen_port')
            
            success = await self.port_forwarder.remove_tunnel(int(listen_port))
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_user_list(self, request):
        """用户列表"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        return web.json_response({"users": self.user_manager.list_users()})
    
    async def handle_user_create(self, request):
        """创建用户"""
        is_valid, result = self._check_permission(request, Permission.ADMIN.value)
        if not is_valid:
            return web.json_response({"error": result}, status=403)
        
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            permissions = data.get('permissions', ['exec', 'file_read'])
            
            if not username or not password:
                return web.json_response({"error": "用户名和密码不能为空"}, status=400)
            
            success = self.user_manager.create_user(username, password, permissions)
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
    
    def _get_index_html(self) -> str:
        """返回主页 HTML（完整版）"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Remote Shell v2.0</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #1a1a2e; color: #eee; }
        .container { max-width: 1400px; margin: 0 auto; }
        
        .login-box { max-width: 400px; margin: 100px auto; background: #16213e; padding: 40px; border-radius: 10px; }
        .login-box h1 { text-align: center; margin-bottom: 30px; color: #4ecca3; }
        .login-box input { width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px; background: #1a1a2e; color: #eee; font-size: 16px; }
        .login-box button { width: 100%; padding: 12px; margin-top: 20px; border: none; border-radius: 5px; background: #4ecca3; color: #1a1a2e; font-size: 16px; cursor: pointer; font-weight: bold; }
        .login-box button:hover { background: #3db892; }
        
        .main-app { display: none; }
        .header { background: #16213e; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #0f3460; }
        .header h1 { color: #4ecca3; font-size: 20px; }
        .header-info { color: #888; font-size: 14px; }
        .header button { padding: 8px 16px; border: none; border-radius: 5px; background: #e94560; color: white; cursor: pointer; }
        
        .tabs { display: flex; background: #16213e; padding: 0 20px; border-bottom: 1px solid #0f3460; overflow-x: auto; }
        .tab { padding: 12px 24px; cursor: pointer; border-bottom: 2px solid transparent; color: #888; white-space: nowrap; }
        .tab.active { color: #4ecca3; border-bottom-color: #4ecca3; }
        .tab:hover { color: #4ecca3; }
        
        .tab-content { padding: 20px; display: none; }
        .tab-content.active { display: block; }
        
        /* 终端 */
        .terminal { background: #0f0f1a; border-radius: 8px; padding: 15px; font-family: "Monaco", "Menlo", monospace; font-size: 14px; height: calc(100vh - 250px); overflow-y: auto; margin-bottom: 15px; }
        .terminal .line { white-space: pre-wrap; word-break: break-all; }
        .terminal .stdout { color: #eee; }
        .terminal .stderr { color: #e94560; }
        .terminal .prompt { color: #4ecca3; }
        .command-input { display: flex; gap: 10px; }
        .command-input input { flex: 1; padding: 12px; border: none; border-radius: 5px; background: #0f0f1a; color: #eee; font-family: monospace; }
        .command-input button { padding: 12px 24px; border: none; border-radius: 5px; background: #4ecca3; color: #1a1a2e; cursor: pointer; font-weight: bold; }
        
        /* 文件管理 */
        .path-bar { display: flex; gap: 10px; margin-bottom: 15px; }
        .path-bar input { flex: 1; padding: 10px; border: none; border-radius: 5px; background: #16213e; color: #eee; }
        .path-bar button { padding: 10px 20px; border: none; border-radius: 5px; background: #4ecca3; color: #1a1a2e; cursor: pointer; }
        .file-list { background: #16213e; border-radius: 8px; max-height: calc(100vh - 250px); overflow-y: auto; }
        .file-item { display: flex; align-items: center; padding: 12px 15px; border-bottom: 1px solid #0f3460; cursor: pointer; }
        .file-item:hover { background: #1a2744; }
        .file-icon { margin-right: 10px; font-size: 20px; }
        .file-name { flex: 1; }
        .file-size { color: #888; margin-right: 20px; }
        
        /* 系统监控 */
        .monitor-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .monitor-card { background: #16213e; border-radius: 8px; padding: 20px; }
        .monitor-card h3 { color: #4ecca3; margin-bottom: 15px; }
        .monitor-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #0f3460; }
        .progress-bar { width: 100%; height: 8px; background: #0f0f1a; border-radius: 4px; margin-top: 5px; }
        .progress-fill { height: 100%; background: #4ecca3; border-radius: 4px; transition: width 0.3s; }
        .progress-fill.warning { background: #f39c12; }
        .progress-fill.danger { background: #e94560; }
        
        /* 隧道管理 */
        .tunnel-form { background: #16213e; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .tunnel-form input { padding: 10px; border: none; border-radius: 5px; background: #1a1a2e; color: #eee; margin-right: 10px; width: 120px; }
        .tunnel-list { background: #16213e; border-radius: 8px; }
        .tunnel-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid #0f3460; }
        .tunnel-item button { padding: 5px 15px; border: none; border-radius: 3px; background: #e94560; color: white; cursor: pointer; }
        
        /* 用户管理 */
        .user-form { background: #16213e; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .user-form input { padding: 10px; border: none; border-radius: 5px; background: #1a1a2e; color: #eee; margin-right: 10px; }
        .user-list { background: #16213e; border-radius: 8px; }
        .user-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid #0f3460; }
        .user-permissions { color: #888; font-size: 12px; }
        
        .error { color: #e94560; text-align: center; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="login-box" id="loginBox">
        <h1>🔺 Remote Shell</h1>
        <input type="text" id="username" placeholder="用户名" value="admin">
        <input type="password" id="password" placeholder="密码">
        <button onclick="login()">登录</button>
        <p id="loginError" class="error"></p>
    </div>
    
    <div class="main-app" id="mainApp">
        <div class="header">
            <h1>🔺 Remote Shell</h1>
            <div class="header-info" id="serverInfo"></div>
            <button onclick="logout()">退出</button>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('terminal')">终端</div>
            <div class="tab" onclick="showTab('files')">文件</div>
            <div class="tab" onclick="showTab('monitor')">监控</div>
            <div class="tab" onclick="showTab('tunnel')">隧道</div>
            <div class="tab" onclick="showTab('users')">用户</div>
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
                <button onclick="listFiles()">浏览</button>
                <button onclick="uploadFile()" style="background:#0f3460;color:#eee;">上传</button>
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
                <h3 style="color:#4ecca3;margin-bottom:15px;">创建隧道</h3>
                <input type="number" id="tunnelListen" placeholder="监听端口">
                <input type="text" id="tunnelHost" placeholder="目标主机">
                <input type="number" id="tunnelPort" placeholder="目标端口">
                <button onclick="createTunnel()" style="padding:10px 20px;background:#4ecca3;color:#1a1a2e;border:none;border-radius:5px;cursor:pointer;">创建</button>
            </div>
            <div class="tunnel-list" id="tunnelList"></div>
        </div>
        
        <!-- 用户管理 -->
        <div class="tab-content" id="usersTab">
            <div class="user-form">
                <h3 style="color:#4ecca3;margin-bottom:15px;">创建用户</h3>
                <input type="text" id="newUsername" placeholder="用户名">
                <input type="password" id="newPassword" placeholder="密码">
                <button onclick="createUser()" style="padding:10px 20px;background:#4ecca3;color:#1a1a2e;border:none;border-radius:5px;cursor:pointer;">创建</button>
            </div>
            <div class="user-list" id="userList"></div>
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
                        <h3>💻 系统</h3>
                        <div class="monitor-row"><span>主机名</span><span>${data.hostname}</span></div>
                        <div class="monitor-row"><span>时间</span><span>${data.time}</span></div>
                        <div class="monitor-row"><span>运行时间</span><span>${data.uptime_days} 天</span></div>
                    </div>
                    <div class="monitor-card">
                        <h3>🖥️ CPU</h3>
                        <div class="monitor-row"><span>使用率</span><span>${data.cpu.usage}%</span></div>
                        <div class="progress-bar"><div class="progress-fill ${pctClass(data.cpu.usage)}" style="width:${data.cpu.usage}%"></div></div>
                        <div class="monitor-row"><span>核心数</span><span>${data.cpu.cores}</span></div>
                        <div class="monitor-row"><span>负载</span><span>${data.cpu.load_avg.join(' / ')}</span></div>
                    </div>
                    <div class="monitor-card">
                        <h3>🧠 内存</h3>
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
                document.getElementById('serverInfo').textContent = `${data.hostname} | CPU: ${data.cpu.usage}% | 内存: ${data.memory.percent}%`;
            } catch (e) {}
        }
        
        async function listTunnels() {
            try {
                const data = await api('/api/tunnel/list');
                const list = document.getElementById('tunnelList');
                list.innerHTML = '<h3 style="color:#4ecca3;padding:15px;">活跃隧道</h3>';
                if (data.tunnels && data.tunnels.length) {
                    data.tunnels.forEach(t => {
                        list.innerHTML += `<div class="tunnel-item">
                            <span>端口 ${t.listen_port} → ${t.target}</span>
                            <span>连接: ${t.connections} | ↑${formatSize(t.bytes_out)} ↓${formatSize(t.bytes_in)}</span>
                            <button onclick="removeTunnel(${t.listen_port})">删除</button>
                        </div>`;
                    });
                } else {
                    list.innerHTML += '<div style="padding:20px;color:#888;text-align:center;">暂无隧道</div>';
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
