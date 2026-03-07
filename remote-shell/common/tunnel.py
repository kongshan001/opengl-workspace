"""
端口转发模块
支持 TCP 端口转发和 SOCKS 代理
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import time


logger = logging.getLogger(__name__)


@dataclass
class TunnelInfo:
    """隧道信息"""
    id: str
    listen_port: int
    target_host: str
    target_port: int
    created_at: float
    connections: int = 0
    bytes_in: int = 0
    bytes_out: int = 0


class PortForwarder:
    """端口转发器"""
    
    def __init__(self):
        self.tunnels: Dict[int, TunnelInfo] = {}
        self.servers: Dict[int, asyncio.Server] = {}
        self._next_id = 1
    
    async def create_tunnel(self, listen_port: int, target_host: str, target_port: int) -> str:
        """创建端口转发隧道"""
        if listen_port in self.tunnels:
            raise ValueError(f"端口 {listen_port} 已被占用")
        
        tunnel_id = str(self._next_id)
        self._next_id += 1
        
        tunnel = TunnelInfo(
            id=tunnel_id,
            listen_port=listen_port,
            target_host=target_host,
            target_port=target_port,
            created_at=time.time()
        )
        
        try:
            server = await asyncio.start_server(
                lambda r, w: self._handle_connection(r, w, tunnel),
                '0.0.0.0',
                listen_port
            )
            
            self.tunnels[listen_port] = tunnel
            self.servers[listen_port] = server
            
            logger.info(f"创建隧道: {listen_port} -> {target_host}:{target_port}")
            return tunnel_id
            
        except Exception as e:
            logger.error(f"创建隧道失败: {e}")
            raise
    
    async def remove_tunnel(self, listen_port: int) -> bool:
        """移除隧道"""
        if listen_port not in self.tunnels:
            return False
        
        server = self.servers.get(listen_port)
        if server:
            server.close()
            await server.wait_closed()
            del self.servers[listen_port]
        
        del self.tunnels[listen_port]
        logger.info(f"移除隧道: {listen_port}")
        return True
    
    async def _handle_connection(
        self, 
        reader: asyncio.StreamReader, 
        writer: asyncio.StreamWriter,
        tunnel: TunnelInfo
    ):
        """处理连接"""
        tunnel.connections += 1
        addr = writer.get_extra_info('peername')
        logger.info(f"隧道 {tunnel.listen_port}: 新连接 {addr}")
        
        try:
            # 连接目标
            target_reader, target_writer = await asyncio.open_connection(
                tunnel.target_host,
                tunnel.target_port
            )
            
            # 双向转发
            async def forward(src: asyncio.StreamReader, dst: asyncio.StreamWriter, is_in: bool):
                try:
                    while True:
                        data = await src.read(4096)
                        if not data:
                            break
                        dst.write(data)
                        await dst.drain()
                        
                        if is_in:
                            tunnel.bytes_in += len(data)
                        else:
                            tunnel.bytes_out += len(data)
                except:
                    pass
                finally:
                    try:
                        dst.close()
                        await dst.wait_closed()
                    except:
                        pass
            
            await asyncio.gather(
                forward(reader, target_writer, True),
                forward(target_reader, writer, False)
            )
            
        except Exception as e:
            logger.error(f"隧道连接错误: {e}")
        finally:
            tunnel.connections -= 1
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
    
    def list_tunnels(self) -> list:
        """列出所有隧道"""
        return [
            {
                "id": t.id,
                "listen_port": t.listen_port,
                "target": f"{t.target_host}:{t.target_port}",
                "connections": t.connections,
                "bytes_in": t.bytes_in,
                "bytes_out": t.bytes_out,
                "uptime": round(time.time() - t.created_at, 0)
            }
            for t in self.tunnels.values()
        ]
    
    async def close_all(self):
        """关闭所有隧道"""
        for port in list(self.tunnels.keys()):
            await self.remove_tunnel(port)


class ReverseTunnel:
    """反向隧道（从服务端连接回客户端）"""
    
    def __init__(self):
        self.tunnels: Dict[str, Tuple[str, int, asyncio.Task]] = {}
    
    async def create(
        self, 
        tunnel_id: str,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        target_host: str,
        target_port: int
    ):
        """创建反向隧道"""
        
        async def tunnel_task():
            try:
                # 连接目标
                target_reader, target_writer = await asyncio.open_connection(
                    target_host, target_port
                )
                
                logger.info(f"反向隧道 {tunnel_id}: 已连接到 {target_host}:{target_port}")
                
                # 双向转发
                async def forward(src, dst):
                    try:
                        while True:
                            data = await src.read(4096)
                            if not data:
                                break
                            dst.write(data)
                            await dst.drain()
                    except:
                        pass
                    finally:
                        try:
                            dst.close()
                            await dst.wait_closed()
                        except:
                            pass
                
                await asyncio.gather(
                    forward(client_reader, target_writer),
                    forward(target_reader, client_writer)
                )
                
            except Exception as e:
                logger.error(f"反向隧道错误: {e}")
            finally:
                if tunnel_id in self.tunnels:
                    del self.tunnels[tunnel_id]
                try:
                    client_writer.close()
                    await client_writer.wait_closed()
                except:
                    pass
        
        task = asyncio.create_task(tunnel_task())
        self.tunnels[tunnel_id] = (f"{target_host}:{target_port}", 0, task)
        
        return tunnel_id
    
    def list_tunnels(self) -> list:
        """列出反向隧道"""
        return [
            {"id": tid, "target": t[0], "bytes": t[1]}
            for tid, t in self.tunnels.items()
        ]
    
    async def close_all(self):
        """关闭所有"""
        for tid, (_, _, task) in list(self.tunnels.items()):
            task.cancel()
            del self.tunnels[tid]
