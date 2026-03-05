# 测试规范

## 测试策略

- **单元测试**: 测试独立的函数和类
- **集成测试**: 测试 API 端点和数据库交互
- **E2E 测试**: 测试完整的用户流程

## 测试文件命名

- 单元测试: `src/**/*.spec.ts`
- 集成测试: `tests/integration/**/*.test.ts`
- E2E 测试: `tests/e2e/**/*.e2e.ts`

## 测试结构

使用 AAA 模式 (Arrange-Act-Assert):

```typescript
describe('UserService', () => {
  describe('getUserById', () => {
    it('should return user when exists', async () => {
      // Arrange
      const mockUser = { id: '1', name: 'Test' };
      mockRepository.findUnique.mockResolvedValue(mockUser);
      
      // Act
      const result = await service.getUserById('1');
      
      // Assert
      expect(result).toEqual(mockUser);
      expect(mockRepository.findUnique).toHaveBeenCalledWith({
        where: { id: '1' }
      });
    });

    it('should return null when not exists', async () => {
      // Arrange
      mockRepository.findUnique.mockResolvedValue(null);
      
      // Act
      const result = await service.getUserById('999');
      
      // Assert
      expect(result).toBeNull();
    });
  });
});
```

## 测试要求

- 覆盖率要求: >= 80%
- 所有新功能必须有测试
- Bug 修复必须有回归测试
- 每个测试只验证一个行为

## Mock 规范

- 使用 Jest 的 mock 功能
- 外部依赖必须 mock
- 数据库操作使用测试数据库

```typescript
// Mock 外部服务
jest.mock('../services/email-service');

// Mock Prisma
const mockPrisma = {
  user: {
    findUnique: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
  },
};
```

## 测试命令

```bash
# 运行所有测试
pnpm test

# 运行特定文件
pnpm test user.service.spec.ts

# 运行带覆盖率
pnpm test:coverage

# 监听模式
pnpm test:watch
```
