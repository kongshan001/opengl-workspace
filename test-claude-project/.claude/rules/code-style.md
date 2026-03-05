# 代码风格规范

所有代码必须遵循以下规范：

## 命名约定

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | kebab-case | `user-service.ts` |
| 类名 | PascalCase | `UserService` |
| 接口 | PascalCase | `IUserRepository` |
| 函数 | camelCase | `getUserById` |
| 变量 | camelCase | `userName` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 私有成员 | _前缀 | `_privateMethod` |

## 代码格式

- 缩进: 2 空格
- 最大行宽: 100 字符
- 使用单引号（字符串）
- 语句末尾不加分号

## 导入顺序

1. Node.js 内置模块
2. 第三方库
3. 项目内部模块
4. 类型导入（使用 `import type`）

```typescript
import { Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';

import { UserService } from './services/user-service';
import { authMiddleware } from './middleware/auth';

import type { User } from './types';
```

## 注释规范

- 公共 API 必须有 JSDoc 注释
- 复杂逻辑必须有行内注释
- 避免无用注释，代码应该自解释

```typescript
/**
 * 获取用户信息
 * @param userId 用户 ID
 * @returns 用户信息，不存在时返回 null
 */
async function getUserById(userId: string): Promise<User | null> {
  // ...
}
```
