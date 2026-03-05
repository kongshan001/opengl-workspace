---
paths:
  - "src/controllers/**/*.ts"
  - "src/routes/**/*.ts"
  - "src/middleware/**/*.ts"
---

# API 开发规范

当处理 API 相关代码时，必须遵循以下规范：

## 端点设计

### RESTful 命名

- 使用名词复数: `/users`, `/orders`, `/products`
- 使用嵌套表示关系: `/users/:userId/orders`
- ❌ 避免动词: ~~`/getUsers`~~
- ✅ 使用 HTTP 方法: `GET /users`

### HTTP 方法

| 方法 | 用途 | 示例 |
|------|------|------|
| GET | 获取资源 | `GET /users` |
| POST | 创建资源 | `POST /users` |
| PUT | 完整更新 | `PUT /users/:id` |
| PATCH | 部分更新 | `PATCH /users/:id` |
| DELETE | 删除资源 | `DELETE /users/:id` |

### 版本控制

- URL 版本: `/api/v1/users`
- Header 版本: `Accept: application/vnd.api+json;version=1`

## 响应格式

### 成功响应

```typescript
// 单个资源
{
  "success": true,
  "data": {
    "id": "1",
    "name": "John Doe"
  }
}

// 列表资源
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5
  }
}
```

### 错误响应

```typescript
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "用户输入验证失败",
    "details": [
      { "field": "email", "message": "邮箱格式不正确" }
    ]
  }
}
```

### HTTP 状态码

| 状态码 | 场景 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无内容） |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 验证失败 |
| 500 | 服务器错误 |

## Controller 结构

```typescript
export class UserController {
  constructor(private readonly userService: UserService) {}

  // GET /users
  async list(req: Request, res: Response): Promise<void> {
    const { page = 1, limit = 20 } = req.query;
    const result = await this.userService.findAll({ page, limit });
    res.json({ success: true, ...result });
  }

  // POST /users
  async create(req: Request, res: Response): Promise<void> {
    const user = await this.userService.create(req.body);
    res.status(201).json({ success: true, data: user });
  }
}
```

## 检查清单

每个 API 端点必须包含：

- [ ] 请求验证 (Zod/Joi)
- [ ] 认证检查 (如需要)
- [ ] 权限验证 (如需要)
- [ ] 错误处理中间件
- [ ] 请求日志
- [ ] API 文档注释
