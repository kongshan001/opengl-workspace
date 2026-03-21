# MEMORY.md - OpenGL 工作空间长期记忆

## 当前项目

### AI Gateway - AI API 代理网关 🔥 NEW
**位置**: `/root/.openclaw/workspace-opengl/ai-gateway/`

**核心功能**:
| 功能 | 说明 |
|------|------|
| 用户管理 | API Key 发放、并发限制、月度配额 |
| API 代理 | OpenAI 兼容格式，转发到上游模型 |
| 负载均衡 | 智能选择最空闲的上游 Key |
| 并发控制 | 单用户并发限制（默认 1），避免超限 |
| 用量统计 | Token 消耗追踪、请求记录 |

**快速使用**:
```bash
cd /root/.openclaw/workspace-opengl/ai-gateway
source venv/bin/activate

# 创建用户
python main.py user create <name> -c 1 -q 100000

# 启动服务
python main.py serve --port 8765

# 调用 API
curl http://localhost:8765/chat/completions \
  -H "Authorization: Bearer gw_xxxx" \
  -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]}'
```

**技术栈**: Python 3 + FastAPI + SQLite + asyncio

**默认端口**: 8765

---

### Remote Shell v2.0 - 远程计算机管理工具
**位置**: `/root/.openclaw/workspace-opengl/remote-shell/`

**功能模块**:
| 模块 | 功能 |
|------|------|
| 终端 | 远程命令执行、交互式 Shell |
| 文件 | 目录浏览、上传/下载 |
| 监控 | CPU/内存/磁盘实时监控 |
| 隧道 | TCP 端口转发 |
| 用户 | 多用户、权限管理 |
| 安全 | Token 认证、TLS 加密 |

**快速使用**:
```bash
# 服务端
cd /root/.openclaw/workspace-opengl/remote-shell
./scripts/start.sh

# Web 访问: http://IP:9528
# 命令行: python3 client/client.py --host <IP> --token <TOKEN>
```

**技术栈**: Python 3 + asyncio + aiohttp

**默认端口**:
- 服务端: 9527
- Web 界面: 9528

## 技术栈

- OpenGL 3.3 Core Profile
- GLSL 330
- C++11/14
- CMake
- GLFW / GLAD

## 开发环境

- Linux 服务器（无物理显示器）
- Xvfb 虚拟显示 :99
- GCC 13.3.0
- CMake 3.28
