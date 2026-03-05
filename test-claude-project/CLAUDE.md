# My API Server

## 项目概述

企业级 REST API 服务，提供业务数据接口和用户管理功能。

## 技术栈

- **语言**: TypeScript 5.x
- **框架**: Express.js 4.x
- **数据库**: PostgreSQL 16
- **ORM**: Prisma 5.x
- **测试**: Jest + Supertest
- **包管理**: pnpm

## 目录结构

```
my-api-server/
├── src/
│   ├── controllers/    # 控制器层
│   ├── services/       # 业务逻辑层
│   ├── repositories/   # 数据访问层
│   ├── middleware/     # 中间件
│   ├── routes/         # 路由定义
│   ├── models/         # 数据模型
│   ├── utils/          # 工具函数
│   └── app.ts          # 应用入口
├── tests/
│   ├── unit/           # 单元测试
│   └── integration/    # 集成测试
├── prisma/
│   └── schema.prisma   # 数据库 Schema
└── docs/               # API 文档
```

## 开发命令

| 操作 | 命令 |
|------|------|
| 安装依赖 | `pnpm install` |
| 开发模式 | `pnpm dev` |
| 构建 | `pnpm build` |
| 测试 | `pnpm test` |
| 测试覆盖率 | `pnpm test:coverage` |
| 代码检查 | `pnpm lint` |
| 格式化 | `pnpm format` |
| 数据库迁移 | `pnpm prisma migrate dev` |

## 编码规范

### TypeScript 规范

- 使用严格模式 (`strict: true`)
- 所有函数必须有返回类型注解
- 避免使用 `any`，使用 `unknown` 或具体类型
- 使用 `interface` 定义对象类型，`type` 定义联合/交叉类型

### 命名约定

- 文件名: `kebab-case.ts`
- 类名: `PascalCase`
- 函数/变量: `camelCase`
- 常量: `UPPER_SNAKE_CASE`

## Git 规范

### 分支命名

- `feature/<ticket-id>-<description>`: 新功能
- `fix/<ticket-id>-<description>`: Bug 修复
- `refactor/<description>`: 代码重构

### 提交信息

```
<type>(<scope>): <subject>

类型: feat, fix, docs, style, refactor, test, chore
```

## 测试规范

- 所有新功能必须有单元测试
- API 端点必须有集成测试
- 测试覆盖率要求: >= 80%
- 测试文件命名: `*.test.ts`

## 注意事项

- 敏感信息禁止提交到代码库
- 所有外部输入必须验证
- API 接口变更需要更新文档
