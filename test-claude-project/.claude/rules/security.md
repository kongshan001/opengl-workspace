# 安全规范

## 认证与授权

- 使用 JWT 进行身份认证
- Token 有效期: 访问令牌 15 分钟，刷新令牌 7 天
- 敏感操作需要二次验证

## 输入验证

- **所有用户输入必须验证和清理**
- 使用 Zod 或 Joi 进行 schema 验证
- 防止 SQL 注入：使用 Prisma 参数化查询
- 防止 XSS：对输出进行 HTML 转义

```typescript
// 使用 Zod 验证
const UserCreateSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(100),
  name: z.string().min(1).max(100),
});

// 验证中间件
const validateBody = (schema: z.ZodSchema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', details: result.error.errors }
      });
    }
    req.body = result.data;
    next();
  };
};
```

## 敏感数据处理

### ❌ 禁止

- 在日志中输出密码、Token
- 在错误信息中暴露内部细节
- 硬编码密钥和凭据
- 提交 `.env` 文件到版本控制

### ✅ 必须

- 使用环境变量存储敏感信息
- 密码使用 bcrypt 加密（cost >= 12）
- API 密钥使用加密存储
- 定期轮换密钥

## 速率限制

| 端点类型 | 限制 |
|----------|------|
| 全局 | 100 请求/分钟/IP |
| 登录 | 5 次/分钟/IP |
| API | 根据用户等级 |

## 依赖安全

```bash
# 定期运行安全审计
pnpm audit

# 自动修复
pnpm audit fix
```

## 错误处理

```typescript
// 生产环境错误响应
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  // 记录完整错误日志
  logger.error('Unhandled error', { error: err, path: req.path });

  // 返回通用错误信息（不暴露内部细节）
  res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_ERROR',
      message: '服务器内部错误'
    }
  });
});
```
