"""
通信协议定义
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MessageType(Enum):
    """消息类型"""
    AUTH = "auth"           # 认证请求
    AUTH_OK = "auth_ok"     # 认证成功
    AUTH_FAIL = "auth_fail" # 认证失败
    EXEC = "exec"           # 执行命令
    OUTPUT = "output"       # 命令输出
    EXIT = "exit"           # 命令结束（包含退出码）
    ERROR = "error"         # 错误
    HEARTBEAT = "heartbeat" # 心跳
    # 文件传输
    FILE_LIST = "file_list"     # 列出文件
    FILE_LIST_RESULT = "file_list_result"  # 文件列表结果
    FILE_DOWNLOAD = "file_download"  # 下载文件
    FILE_DATA = "file_data"    # 文件数据
    FILE_UPLOAD = "file_upload"  # 上传文件
    FILE_DONE = "file_done"    # 文件传输完成


@dataclass
class Message:
    """消息结构"""
    type: MessageType
    data: dict
    request_id: Optional[str] = None
    
    def encode(self) -> bytes:
        """编码为字节流"""
        obj = {
            "type": self.type.value,
            "data": self.data,
            "request_id": self.request_id
        }
        json_str = json.dumps(obj, ensure_ascii=False)
        # 格式: 4字节长度 + JSON数据
        encoded = json_str.encode('utf-8')
        length = len(encoded)
        return length.to_bytes(4, 'big') + encoded
    
    @classmethod
    def decode(cls, data: bytes) -> 'Message':
        """从字节流解码"""
        obj = json.loads(data.decode('utf-8'))
        return cls(
            type=MessageType(obj["type"]),
            data=obj["data"],
            request_id=obj.get("request_id")
        )


def create_auth_message(token: str) -> Message:
    """创建认证消息"""
    return Message(MessageType.AUTH, {"token": token})


def create_exec_message(command: str, request_id: str = None) -> Message:
    """创建执行命令消息"""
    return Message(MessageType.EXEC, {"command": command}, request_id)


def create_output_message(output: str, stream: str = "stdout", request_id: str = None) -> Message:
    """创建输出消息"""
    return Message(
        MessageType.OUTPUT, 
        {"output": output, "stream": stream}, 
        request_id
    )


def create_exit_message(code: int, request_id: str = None) -> Message:
    """创建退出消息"""
    return Message(MessageType.EXIT, {"code": code}, request_id)


def create_error_message(error: str, request_id: str = None) -> Message:
    """创建错误消息"""
    return Message(MessageType.ERROR, {"error": error}, request_id)


def create_auth_ok_message() -> Message:
    """创建认证成功消息"""
    return Message(MessageType.AUTH_OK, {})


def create_auth_fail_message(reason: str) -> Message:
    """创建认证失败消息"""
    return Message(MessageType.AUTH_FAIL, {"reason": reason})


def create_file_list_message(path: str = ".", request_id: str = None) -> Message:
    """创建文件列表请求"""
    return Message(MessageType.FILE_LIST, {"path": path}, request_id)


def create_file_list_result_message(files: list, request_id: str = None) -> Message:
    """创建文件列表结果"""
    return Message(MessageType.FILE_LIST_RESULT, {"files": files}, request_id)


def create_file_download_message(path: str, request_id: str = None) -> Message:
    """创建文件下载请求"""
    return Message(MessageType.FILE_DOWNLOAD, {"path": path}, request_id)


def create_file_data_message(data: bytes, offset: int, total: int, request_id: str = None) -> Message:
    """创建文件数据消息"""
    import base64
    return Message(
        MessageType.FILE_DATA, 
        {
            "data": base64.b64encode(data).decode('ascii'),
            "offset": offset,
            "total": total
        }, 
        request_id
    )


def create_file_upload_message(path: str, data: bytes, offset: int, total: int, request_id: str = None) -> Message:
    """创建文件上传消息"""
    import base64
    return Message(
        MessageType.FILE_UPLOAD,
        {
            "path": path,
            "data": base64.b64encode(data).decode('ascii'),
            "offset": offset,
            "total": total
        },
        request_id
    )


def create_file_done_message(success: bool, message: str = "", request_id: str = None) -> Message:
    """创建文件传输完成消息"""
    return Message(MessageType.FILE_DONE, {"success": success, "message": message}, request_id)
