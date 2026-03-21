# AI Gateway 测试报告

**测试时间**: 2026-03-13 22:37  
**测试环境**: Linux (Ubuntu 24.04), Python 3.12  
**上游模型**: GLM-5 (智谱 AI Coding Plan)

---

## 测试概要

| 测试项 | 结果 |
|--------|------|
| 服务启动 | ✅ 通过 |
| 用户创建 | ✅ 通过 |
| API 调用 | ✅ 通过 |
| 负载均衡 | ✅ 通过 |
| 并发控制 | ✅ 通过 |
| 认证鉴权 | ✅ 通过 |
| 用量统计 | ✅ 通过 |

**总体结论**: 🎉 **所有测试通过**

---

## 详细测试结果

### 1. 服务启动测试 ✅

```
服务: AI Gateway v1.0.0
监听: http://0.0.0.0:8765
上游 Key 加载: 2 个
健康检查: {"status":"ok"}
```

### 2. 用户管理测试 ✅

**创建用户**:
```
名称: test-alice
API Key: gw_5ec446e7277c2835e177e8b9d69c8641
并发限制: 1
月度配额: 50,000 tokens
```

**用户列表**:
| ID | 名称 | 并发 | 配额 | 已用 | 状态 |
|----|------|------|------|------|------|
| 89332248 | test-alice | 0/1 | 50,000 | 838 | 活跃 |
| 8910366c | test-user | 0/1 | 100,000 | 0 | 活跃 |

### 3. API 调用测试 ✅

**请求**:
```bash
curl -X POST http://localhost:8765/chat/completions \
  -H "Authorization: Bearer gw_xxxx" \
  -d '{"model": "glm-5", "messages": [{"role": "user", "content": "1+1=?"}]}'
```

**响应**:
```json
{
  "model": "glm-5",
  "choices": [{"message": {"content": "1+1等于2。"}}],
  "usage": {
    "prompt_tokens": 16,
    "completion_tokens": 287,
    "total_tokens": 303
  }
}
```

### 4. 负载均衡测试 ✅

**策略**: `least_loaded` (选择并发最少的 Key)

**状态**:
```
glm-1: 并发 0/2, 可用槽位: 2
glm-2: 并发 0/2, 可用槽位: 2

总请求: 3
成功: 3
失败: 0
```

### 5. 并发控制测试 ✅

**场景**: 用户并发限制为 1，同时发起 2 个请求

**结果**: 两个请求都成功完成（第二个请求自动排队等待）

**说明**: 系统通过用户锁实现串行处理，确保不超过并发限制

### 6. 认证鉴权测试 ✅

**无效 API Key**:
```json
{"detail":"无效的 API Key"}
```

**响应**: 401 Unauthorized

### 7. 用量统计测试 ✅

- Token 消耗被正确记录到数据库
- 用户已用量实时更新
- 请求记录保存到 SQLite

---

## 数据存储

- **数据库**: SQLite
- **位置**: `data/gateway.db`
- **大小**: 24 KB

---

## 性能指标

| 指标 | 值 |
|------|-----|
| 请求成功率 | 100% (3/3) |
| 平均响应时间 | ~3 秒 (取决于上游模型) |
| 并发处理 | 正常（用户级串行） |

---

## 待优化项

1. **流式响应**: 已实现但未测试
2. **Web 管理界面**: 未实现
3. **计费系统**: 仅统计，未实现扣费逻辑
4. **监控告警**: 未实现

---

## 快速使用

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
  -d '{"model": "glm-5", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

*测试完成 ✅*
