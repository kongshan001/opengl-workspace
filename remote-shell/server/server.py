#!/usr/bin/env python3
"""
远程 Shell 服务端（增强版）
支持：命令执行、文件传输、TLS 加密、配置管理
"""

import asyncio
import subprocess
import os
import sys
import ssl
import logging
import argparse
from typing import Dict, Optional
import uuid
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.protocol import (
    Message, MessageType,
    create_output_message, create_exit_message, create_error_message,
    create_file_list_result_message, create_file_data_message, create_file_done_message
)
from common.config import Config
from common.audit import audit_log, AuditEventType


# 配置日志
def setup_logging(config: Config):
    os.makedirs(os.path.dirname(config.log.file), exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, config.log.level),
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(config.log.file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


class ClientSession:
    """客户端会话"""
    def __init__(self, writer: asyncio.StreamWriter, config: Config):
        self.writer = writer
        self.config = config
        self.authenticated = False
        self.running_processes: Dict[str, asyncio.subprocess.Process] = {}
        self.logger = logging.getLogger(__name__)
        self.ip_address = ""
        self.username = ""
    
    async def send(self, msg: Message):
        """发送消息"""
        try:
            self.writer.write(msg.encode())
            await self.writer.drain()
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")


class RemoteShellServer:
    """远程 Shell 服务器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.clients: Dict[str, ClientSession] = {}
        self.logger = logging.getLogger(__name__)
        
        print(f"[Server] 配置加载完成")
        print(f"[Server] 监听地址: {config.server.host}:{config.server.port}")
        print(f"[Server] 认证 Token: {config.server.token}")
        if config.tls.enabled:
            print(f"[Server] TLS 已启用")
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接"""
        client_id = str(uuid.uuid4())[:8]
        session = ClientSession(writer, self.config)
        self.clients[client_id] = session
        
        addr = writer.get_extra_info('peername')
        session.ip_address = addr[0] if addr else "unknown"
        self.logger.info(f"新连接: {addr} (ID: {client_id})")
        
        audit_log(
            AuditEventType.CLIENT_CONNECT,
            ip_address=session.ip_address,
            description=f"客户端连接 (ID: {client_id})"
        )
        
        try:
            await self._read_loop(client_id, session, reader)
        except Exception as e:
            self.logger.error(f"客户端 {client_id} 错误: {e}")
        finally:
            await self._cleanup_client(client_id, session)
    
    async def _read_loop(self, client_id: str, session: ClientSession, reader: asyncio.StreamReader):
        """消息读取循环"""
        while True:
            try:
                length_data = await reader.readexactly(4)
                length = int.from_bytes(length_data, 'big')
                data = await reader.readexactly(length)
                msg = Message.decode(data)
                
                await self._handle_message(client_id, session, msg)
                
            except asyncio.IncompleteReadError:
                self.logger.info(f"客户端 {client_id} 断开连接")
                break
            except Exception as e:
                self.logger.error(f"解析消息错误: {e}")
                break
    
    async def _handle_message(self, client_id: str, session: ClientSession, msg: Message):
        """处理消息"""
        if msg.type == MessageType.AUTH:
            await self._handle_auth(session, msg)
        elif msg.type == MessageType.HEARTBEAT:
            pass
        elif not session.authenticated:
            await session.send(create_error_message("未认证", msg.request_id))
        elif msg.type == MessageType.EXEC:
            await self._handle_exec(session, msg)
        elif msg.type == MessageType.FILE_LIST:
            await self._handle_file_list(session, msg)
        elif msg.type == MessageType.FILE_DOWNLOAD:
            await self._handle_file_download(session, msg)
        elif msg.type == MessageType.FILE_UPLOAD:
            await self._handle_file_upload(session, msg)
        else:
            await session.send(create_error_message(f"未知消息类型: {msg.type}", msg.request_id))
    
    async def _handle_auth(self, session: ClientSession, msg: Message):
        """处理认证"""
        token = msg.data.get("token", "")
        username = msg.data.get("username", "api_client")
        if token == self.config.server.token:
            session.authenticated = True
            session.username = username
            await session.send(Message(MessageType.AUTH_OK, {}))
            self.logger.info("认证成功")
            audit_log(
                AuditEventType.LOGIN_SUCCESS,
                username=username,
                ip_address=session.ip_address,
                description="API 认证成功"
            )
        else:
            await session.send(Message(MessageType.AUTH_FAIL, {"reason": "Token 错误"}))
            self.logger.warning("认证失败: Token 不匹配")
            audit_log(
                AuditEventType.LOGIN_FAILED,
                username=username,
                ip_address=session.ip_address,
                description="Token 认证失败",
                success=False
            )
    
    async def _handle_exec(self, session: ClientSession, msg: Message):
        """处理命令执行"""
        command = msg.data.get("command", "")
        request_id = msg.request_id
        
        if not command:
            await session.send(create_error_message("命令为空", request_id))
            return
        
        self.logger.info(f"执行命令: {command}")
        audit_log(
            AuditEventType.COMMAND_EXEC,
            username=session.username,
            ip_address=session.ip_address,
            description=f"执行命令: {command[:100]}",
            details={"command": command, "request_id": request_id}
        )
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            if request_id:
                session.running_processes[request_id] = process
            
            async def read_stream(stream, stream_name):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    try:
                        output = line.decode('utf-8', errors='replace')
                        await session.send(create_output_message(output, stream_name, request_id))
                    except Exception as e:
                        self.logger.error(f"发送输出错误: {e}")
            
            await asyncio.gather(
                read_stream(process.stdout, "stdout"),
                read_stream(process.stderr, "stderr")
            )
            
            exit_code = await process.wait()
            await session.send(create_exit_message(exit_code, request_id))
            
            self.logger.info(f"命令完成，退出码: {exit_code}")
            audit_log(
                AuditEventType.COMMAND_SUCCESS if exit_code == 0 else AuditEventType.COMMAND_FAILED,
                username=session.username,
                ip_address=session.ip_address,
                description=f"命令完成 (退出码: {exit_code})",
                details={"command": command[:100], "exit_code": exit_code},
                success=(exit_code == 0)
            )
            
        except Exception as e:
            await session.send(create_error_message(f"执行错误: {e}", request_id))
            audit_log(
                AuditEventType.COMMAND_FAILED,
                username=session.username,
                ip_address=session.ip_address,
                description=f"命令执行异常: {e}",
                details={"command": command[:100], "error": str(e)},
                success=False
            )
        finally:
            if request_id and request_id in session.running_processes:
                del session.running_processes[request_id]
    
    async def _handle_file_list(self, session: ClientSession, msg: Message):
        """处理文件列表请求"""
        path = msg.data.get("path", ".")
        request_id = msg.request_id
        
        audit_log(
            AuditEventType.FILE_LIST,
            username=session.username,
            ip_address=session.ip_address,
            description=f"列出目录: {path}",
            details={"path": path}
        )
        
        try:
            path = os.path.abspath(os.path.expanduser(path))
            
            if not os.path.exists(path):
                await session.send(create_error_message(f"路径不存在: {path}", request_id))
                return
            
            files = []
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
                    stat = os.stat(item_path)
                    files.append({
                        "name": item,
                        "path": item_path,
                        "type": "directory" if os.path.isdir(item_path) else "file",
                        "size": stat.st_size if os.path.isfile(item_path) else 0,
                        "modified": stat.st_mtime
                    })
            
            await session.send(create_file_list_result_message(files, request_id))
            self.logger.info(f"列出文件: {path} ({len(files)} 项)")
            
        except Exception as e:
            await session.send(create_error_message(f"列出文件失败: {e}", request_id))
    
    async def _handle_file_download(self, session: ClientSession, msg: Message):
        """处理文件下载"""
        path = msg.data.get("path", "")
        request_id = msg.request_id
        
        try:
            path = os.path.abspath(os.path.expanduser(path))
            
            if not os.path.isfile(path):
                await session.send(create_error_message(f"文件不存在: {path}", request_id))
                return
            
            file_size = os.path.getsize(path)
            self.logger.info(f"下载文件: {path} ({file_size} bytes)")
            audit_log(
                AuditEventType.FILE_DOWNLOAD,
                username=session.username,
                ip_address=session.ip_address,
                description=f"下载文件: {path}",
                details={"path": path, "size": file_size}
            )
            
            CHUNK_SIZE = 64 * 1024  # 64KB
            offset = 0
            
            with open(path, 'rb') as f:
                while offset < file_size:
                    data = f.read(CHUNK_SIZE)
                    await session.send(create_file_data_message(data, offset, file_size, request_id))
                    offset += len(data)
            
            await session.send(create_file_done_message(True, f"下载完成: {file_size} bytes", request_id))
            
        except Exception as e:
            await session.send(create_file_done_message(False, str(e), request_id))
    
    async def _handle_file_upload(self, session: ClientSession, msg: Message):
        """处理文件上传"""
        path = msg.data.get("path", "")
        data_b64 = msg.data.get("data", "")
        request_id = msg.request_id
        
        try:
            path = os.path.abspath(os.path.expanduser(path))
            data = base64.b64decode(data_b64)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'ab') as f:
                f.write(data)
            
            self.logger.info(f"上传数据: {path} (+{len(data)} bytes)")
            audit_log(
                AuditEventType.FILE_UPLOAD,
                username=session.username,
                ip_address=session.ip_address,
                description=f"上传文件: {path}",
                details={"path": path, "size": len(data)}
            )
            
        except Exception as e:
            await session.send(create_file_done_message(False, str(e), request_id))
    
    async def _cleanup_client(self, client_id: str, session: ClientSession):
        """清理客户端资源"""
        for proc in session.running_processes.values():
            try:
                proc.terminate()
                await asyncio.sleep(0.5)
                if proc.returncode is None:
                    proc.kill()
            except:
                pass
        
        session.writer.close()
        try:
            await session.writer.wait_closed()
        except:
            pass
        
        if client_id in self.clients:
            del self.clients[client_id]
        
        self.logger.info(f"客户端 {client_id} 已清理")
        audit_log(
            AuditEventType.CLIENT_DISCONNECT,
            username=session.username,
            ip_address=session.ip_address,
            description=f"客户端断开 (ID: {client_id})"
        )
    
    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """创建 SSL 上下文"""
        if not self.config.tls.enabled:
            return None
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            self.config.tls.cert_file,
            self.config.tls.key_file
        )
        return context
    
    async def run(self):
        """启动服务器"""
        ssl_context = self.create_ssl_context()
        
        server = await asyncio.start_server(
            self.handle_client,
            self.config.server.host,
            self.config.server.port,
            ssl=ssl_context
        )
        
        addr = server.sockets[0].getsockname()
        print(f"[Server] 监听 {addr[0]}:{addr[1]}")
        print(f"[Server] 按 Ctrl+C 停止")
        
        async with server:
            await server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="远程 Shell 服务端")
    parser.add_argument("--config", default="/etc/remote-shell/config.json", help="配置文件路径")
    parser.add_argument("--host", help="监听地址（覆盖配置文件）")
    parser.add_argument("--port", type=int, help="监听端口（覆盖配置文件）")
    parser.add_argument("--token", help="认证 Token（覆盖配置文件）")
    
    args = parser.parse_args()
    
    # 加载配置
    if os.path.exists(args.config):
        config = Config.load(args.config)
    else:
        print(f"[!] 配置文件不存在: {args.config}")
        print(f"[*] 使用默认配置...")
        config = Config()
        if not config.server.token:
            import secrets
            config.server.token = secrets.token_hex(16)
    
    # 命令行参数覆盖
    if args.host:
        config.server.host = args.host
    if args.port:
        config.server.port = args.port
    if args.token:
        config.server.token = args.token
    
    setup_logging(config)
    
    server = RemoteShellServer(config)
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n[Server] 已停止")


if __name__ == "__main__":
    main()
