# AI Gateway - AI API 代理网关

一个轻量级的 AI API 代理服务，支持多上游 Key 池和智能负载均衡。

## 功能特性

- ✅ **用户管理**: API Key 发放、并发限制、月度配额
- ✅ **负载均衡**: 智能调度，选择最空闲的上游 Key
- ✅ **并发控制**: 单用户并发限制，避免超限
- ✅ **用量统计**: Token 消耗追踪
- ✅ **OpenAI 兼容**: 完全兼容 OpenAI API 格式

## 快速开始

### 1. 安装依赖

```bash
cd ai-gateway
pip install -r requirements.txt
```

### 2. 配置上游 Key

编辑 `config/settings.yaml`，或设置环境变量：

```bash
export JOINER_API_KEY_1="your-key-1"
export JOINER_API_KEY_2="your-key-2"
```

### 3. 启动服务

```bash
python main.py serve
# 或指定端口
python main.py serve --port 9000
```

### 4. 创建用户

```bash
# 创建用户
python main.py user create alice --concurrent 1 --quota 100000

# 查看用户列表
python main.py user list
```

### 5. 调用 API

```bash
curl http://localhost:8765/chat/completions \
  -H "Authorization: Bearer gw_xxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## CLI 命令

```bash
# 服务管理
python main.py serve              # 启动服务
python main.py serve --port 9000  # 指定端口

# 用户管理
python main.py user create <name>           # 创建用户
python main.py user create <name> -c 2      # 并发限制为 2
python main.py user create <name> -q 500000 # 配额 50 万 tokens
python main.py user list                    # 列出用户
python main.py user stats <user_id>         # 查看统计

# 上游管理
python main.py upstream status   # 查看上游 Key 状态

# 配置管理
python main.py config show       # 显示配置
python main.py config init       # 初始化配置

# 测试
python main.py test --api-key gw_xxxx --message "Hello"
```

## 架构

```
┌─────────────┐     ┌──────────────────────────┐     ┌──────────────┐
│    用户     │────▶│      AI Gateway          │────▶│  上游 Keys   │
│  (API Key)  │◀────│  - 认证 & 并发控制        │◀────│  - Joiner    │
└─────────────┘     │  - 负载均衡              │     │  - OpenAI    │
                    │  - 用量统计              │     │  - Claude    │
                    └──────────────────────────┘     └──────────────┘
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat/completions` | POST | 聊天完成（需 Authorization） |
| `/v1/chat/completions` | POST | 同上（兼容路径） |
| `/status` | GET | 系统状态 |
| `/health` | GET | 健康检查 |
| `/admin/users` | POST | 创建用户 |
| `/admin/users` | GET | 列出用户 |
| `/admin/users/{id}/stats` | GET | 用户统计 |

## 配置说明

```yaml
# config/settings.yaml

server:
  host: "0.0.0.0"
  port: 8765

# 上游 Key 池
upstream_keys:
  - name: "joiner-1"
    provider: "joiner"
    api_key: "${JOINER_API_KEY_1}"  # 支持环境变量
    base_url: "https://api.joiner.ai/v1"
    max_concurrent: 2
    enabled: true

# 用户限制
user_limits:
  max_concurrent: 1
  default_monthly_quota: 1000000

# 负载均衡策略: least_loaded | round_robin | random
load_balance:
  strategy: "least_loaded"
```

## 数据存储

默认使用 SQLite，数据文件位于 `data/gateway.db`。

## 许可证

MIT
