#!/usr/bin/env python3
"""
远程 Shell 客户端
连接到服务端并发送命令
"""

import asyncio
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.protocol import (
    Message, MessageType,
    create_auth_message, create_exec_message
)


class RemoteShellClient:
    """远程 Shell 客户端"""
    
    def __init__(self, host: str, port: int, token: str):
        self.host = host
        self.port = port
        self.token = token
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.authenticated = False
    
    async def connect(self):
        """连接到服务器"""
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )
        print(f"[Client] 已连接到 {self.host}:{self.port}")
        
        # 发送认证
        await self._send(create_auth_message(self.token))
        
        # 等待认证响应
        response = await self._recv()
        if response.type == MessageType.AUTH_OK:
            self.authenticated = True
            print("[Client] 认证成功")
            return True
        else:
            reason = response.data.get("reason", "未知原因")
            print(f"[Client] 认证失败: {reason}")
            await self.close()
            return False
    
    async def close(self):
        """关闭连接"""
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except:
                pass
        print("[Client] 连接已关闭")
    
    async def _send(self, msg: Message):
        """发送消息"""
        self.writer.write(msg.encode())
        await self.writer.drain()
    
    async def _recv(self) -> Message:
        """接收消息"""
        length_data = await self.reader.readexactly(4)
        length = int.from_bytes(length_data, 'big')
        data = await self.reader.readexactly(length)
        return Message.decode(data)
    
    async def execute(self, command: str) -> int:
        """执行命令并返回退出码"""
        if not self.authenticated:
            print("[Client] 未认证")
            return -1
        
        import uuid
        request_id = str(uuid.uuid4())[:8]
        
        await self._send(create_exec_message(command, request_id))
        
        exit_code = 0
        
        # 接收输出
        while True:
            try:
                msg = await self._recv()
                
                if msg.type == MessageType.OUTPUT:
                    output = msg.data.get("output", "")
                    stream = msg.data.get("stream", "stdout")
                    # 直接输出到对应流
                    if stream == "stderr":
                        sys.stderr.write(output)
                        sys.stderr.flush()
                    else:
                        sys.stdout.write(output)
                        sys.stdout.flush()
                
                elif msg.type == MessageType.EXIT:
                    exit_code = msg.data.get("code", 0)
                    break
                
                elif msg.type == MessageType.ERROR:
                    error = msg.data.get("error", "未知错误")
                    print(f"[Error] {error}", file=sys.stderr)
                    break
            
            except asyncio.IncompleteReadError:
                print("[Client] 连接已断开", file=sys.stderr)
                break
            except Exception as e:
                print(f"[Client] 接收错误: {e}", file=sys.stderr)
                break
        
        return exit_code
    
    async def interactive(self):
        """交互式 Shell"""
        if not self.authenticated:
            return
        
        print("[Client] 进入交互模式，输入 'exit' 退出\n")
        
        while True:
            try:
                # 读取命令
                command = input("$ ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ("exit", "quit"):
                    break
                
                # 执行命令
                exit_code = await self.execute(command)
                
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n[Client] 按 Ctrl+D 退出")
            except Exception as e:
                print(f"[Client] 错误: {e}", file=sys.stderr)
        
        print("\n[Client] 退出交互模式")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="远程 Shell 客户端")
    parser.add_argument("--host", required=True, help="服务器地址")
    parser.add_argument("--port", type=int, default=9527, help="服务器端口")
    parser.add_argument("--token", required=True, help="认证 Token")
    parser.add_argument("-c", "--command", help="要执行的命令（不指定则进入交互模式）")
    
    args = parser.parse_args()
    
    client = RemoteShellClient(args.host, args.port, args.token)
    
    try:
        if await client.connect():
            if args.command:
                # 单次命令模式
                exit_code = await client.execute(args.command)
                sys.exit(exit_code)
            else:
                # 交互模式
                await client.interactive()
    except ConnectionRefusedError:
        print(f"[Client] 无法连接到 {args.host}:{args.port}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[Client] 错误: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
