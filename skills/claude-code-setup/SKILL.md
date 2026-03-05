---
name: claude-code-setup
description: 一键生成完整的 .claude 工程目录结构，基于最新的 Claude Code 官方文档。包含 CLAUDE.md、settings.json、rules、skills、agents、hooks、MCP 配置等。当用户想要为 Claude Code 配置项目、初始化 .claude 目录、或设置 Claude Code 工作环境时使用。
argument-hint: [project-path]
---

# Claude Code 项目配置生成器

此技能帮助你快速搭建 Claude Code 项目的完整配置结构，基于最新的 Claude Code 官方文档。

## 使用方式

1. **交互式生成**: 直接运行 `/claude-code-setup`，我会引导你完成配置
2. **指定路径**: `/claude-code-setup /path/to/your/project`

---

## 执行流程

当用户运行此技能时，**必须**按以下步骤交互式收集信息并生成配置。

### 步骤 0: 确认目标目录

首先确认配置生成的目标目录：
- 如果用户提供了参数 `$ARGUMENTS`，使用该路径
- 否则询问用户目标项目路径
- 默认为当前工作目录

**重要**: 在开始之前，检查目标目录是否已有 `.claude/` 目录。如果存在，询问用户是否要：
1. 覆盖现有配置
2. 合并（保留已有文件，只添加缺失的）
3. 取消操作

---

### 步骤 1: 收集项目基本信息

使用 AskUserQuestion 或直接对话询问用户：

**问题 1.1 - 项目名称**
> 请输入项目名称（用于 CLAUDE.md 标题）:

**问题 1.2 - 项目类型**（单选）
> 请选择项目类型：
> 1. 🌐 Web Frontend (React/Vue/Angular/Svelte)
> 2. 🔧 Web Backend (Node.js/Python/Go/Java)
> 3. 📱 Mobile App (React Native/Flutter/Native)
> 4. 💻 CLI Tool
> 5. 📦 Library/Package
> 6. 🖥️ Desktop App (Electron/Tauri)
> 7. 🎮 Game Development
> 8. 🔬 Other

**问题 1.3 - 主要语言**（单选）
> 请选择主要编程语言：
> 1. TypeScript
> 2. JavaScript
> 3. Python
> 4. Go
> 5. Rust
> 6. Java
> 7. C/C++
> 8. Other

**问题 1.4 - 框架/工具**
> 请输入使用的主要框架或工具（如 React, Express, Django, FastAPI, Next.js 等），多个用逗号分隔:

**问题 1.5 - 项目描述**
> 请简要描述项目功能和目标（1-2 句话）:

---

### 步骤 2: 选择配置模块

**问题 2.1 - 需要生成的配置**（多选）
> 请选择需要生成的配置模块（可多选）：
> 
> | 选项 | 模块 | 说明 |
> |------|------|------|
> | [x] | CLAUDE.md | 项目上下文和指令（必选） |
> | [ ] | Rules | 模块化规则目录 |
> | [ ] | Skills | 自定义技能 |
> | [ ] | Agents | 自定义 Subagent |
> | [ ] | Hooks | 生命周期钩子 |
> | [ ] | MCP | MCP 服务器配置 |
> | [ ] | Settings | 权限和环境配置 |

默认全部选中，用户可以取消不需要的。

---

### 步骤 3: CLAUDE.md 内容配置

根据项目类型，询问需要包含的内容：

**问题 3.1 - CLAUDE.md 内容**（多选）
> 请选择 CLAUDE.md 中需要包含的内容：
> 
> | 选项 | 内容 |
> |------|------|
> | [x] | 技术栈说明 |
> | [x] | 目录结构 |
> | [x] | 开发命令 |
> | [ ] | 编码规范 |
> | [ ] | 测试规范 |
> | [ ] | Git 规范 |
> | [ ] | API 文档（如果是 API 项目） |
> | [ ] | 部署说明 |
> | [ ] | 自定义指令 |

**问题 3.2 - 自定义指令**（如果选择了自定义指令）
> 请输入任何需要添加到 CLAUDE.md 的自定义指令:

---

### 步骤 4: Rules 配置（如果选择了 Rules）

**问题 4.1 - 规则类型**（多选）
> 请选择需要创建的规则文件：
> 
> **通用规则**（启动时加载）:
> | 选项 | 文件 | 说明 |
> |------|------|------|
> | [ ] | code-style.md | 代码风格和命名约定 |
> | [ ] | testing.md | 测试编写规范 |
> | [ ] | security.md | 安全编码要求 |
> | [ ] | git.md | Git 工作流规范 |
> 
> **路径特定规则**（条件加载）:
> | 选项 | 文件 | 匹配路径 |
> |------|------|----------|
> | [ ] | api-design.md | API 相关代码 |
> | [ ] | frontend-components.md | 前端组件 |
> | [ ] | database.md | 数据库操作 |
> | [ ] | cli-commands.md | CLI 命令处理 |

根据项目类型智能推荐默认选项：
- Frontend: code-style, testing, frontend-components
- Backend: code-style, testing, security, api-design, database
- CLI: code-style, testing, cli-commands
- Library: code-style, testing

**问题 4.2 - 是否创建用户级规则**
> 是否同时在 `~/.claude/rules/` 创建用户级规则？（适用于所有项目）
> 1. 是
> 2. 否（默认）

---

### 步骤 5: Skills 配置（如果选择了 Skills）

**问题 5.1 - 示例 Skills**（多选）
> 请选择需要创建的示例 Skills：
> 
> | 选项 | Skill | 说明 |
> |------|-------|------|
> | [ ] | review-pr | PR 代码审查 |
> | [ ] | run-tests | 运行测试并分析结果 |
> | [ ] | generate-docs | 生成 API 文档 |
> | [ ] | deploy | 部署流程自动化 |
> | [ ] | create-component | 创建新组件（Frontend） |
> | [ ] | create-api | 创建新 API 端点（Backend） |
> | [ ] | release | 发布新版本 |

根据项目类型智能推荐。

**问题 5.2 - 自定义 Skill**
> 是否需要创建自定义 Skill？
> 1. 是 - 请描述 Skill 功能
> 2. 否（默认）

---

### 步骤 6: Agents 配置（如果选择了 Agents）

**问题 6.1 - 示例 Agents**（多选）
> 请选择需要创建的示例 Agents：
> 
> | 选项 | Agent | 工具 | 说明 |
> |------|-------|------|------|
> | [ ] | test-writer | Read, Write, Edit, Bash | 编写测试用例 |
> | [ ] | code-reviewer | Read, Grep, Glob | 代码审查 |
> | [ ] | doc-writer | Read, Write | 编写文档 |
> | [ ] | refactor | Read, Write, Edit | 代码重构 |
> | [ ] | db-analyst | Read, Bash | 数据库分析 |

**问题 6.2 - Agent 模型选择**
> 默认使用什么模型？
> 1. inherit（继承主会话模型，默认）
> 2. sonnet
> 3. haiku（快速任务）
> 4. opus（复杂任务）

---

### 步骤 7: Hooks 配置（如果选择了 Hooks）

**问题 7.1 - Hook 类型**（多选）
> 请选择需要配置的 Hooks：
> 
> | 选项 | Hook | 触发时机 | 用途示例 |
> |------|------|----------|----------|
> | [ ] | PreToolUse | 工具执行前 | 验证危险命令 |
> | [ ] | PostToolUse | 工具执行后 | 自动格式化 |
> | [ ] | SessionStart | 会话开始 | 加载环境 |
> | [ ] | UserPromptSubmit | 提交提示词时 | 过滤敏感词 |

**问题 7.2 - PreToolUse 配置**（如果选择了）
> PreToolUse 需要验证哪些操作？
> 1. 禁止危险 Bash 命令（rm -rf, curl | bash 等）
> 2. 保护敏感文件（.env, *.pem, *.key）
> 3. 全部启用（默认）

---

### 步骤 8: MCP 配置（如果选择了 MCP）

**问题 8.1 - MCP 服务器**（多选）
> 请选择需要配置的 MCP 服务器：
> 
> **官方服务器**:
> | 选项 | 服务器 | 用途 |
> |------|--------|------|
> | [ ] | GitHub | GitHub 操作 |
> | [ ] | Memory | 持久化记忆 |
> | [ ] | Filesystem | 文件系统增强 |
> 
> **数据库**:
> | 选项 | 服务器 | 用途 |
> |------|--------|------|
> | [ ] | PostgreSQL | PostgreSQL 数据库 |
> | [ ] | SQLite | SQLite 数据库 |
> 
> **第三方服务**:
> | 选项 | 服务器 | 用途 |
> |------|--------|------|
> | [ ] | Slack | Slack 通知 |
> | [ ] | Sentry | 错误监控 |
> | [ ] | Notion | Notion 集成 |

**问题 8.2 - MCP Scope**
> MCP 配置保存位置？
> 1. Project（`.mcp.json`，团队共享，默认）
> 2. Local（`~/.claude.json`，仅本机）

---

### 步骤 9: Settings 配置（如果选择了 Settings）

**问题 9.1 - 权限模式**
> 选择默认权限模式：
> 1. default（标准权限检查，默认）
> 2. acceptEdits（自动接受文件编辑）
> 3. plan（计划模式，只读）
> 4. dontAsk（自动拒绝未授权操作）

**问题 9.2 - 预授权工具**
> 哪些工具操作需要预授权（不需要每次确认）？
> 1. 常用开发命令（npm/pnpm, git）
> 2. 全部读取操作
> 3. 全部（不推荐）
> 4. 手动选择

**问题 9.3 - 禁止操作**
> 哪些操作需要禁止？
> 1. 读取敏感文件（.env, secrets/）
> 2. 危险 Bash 命令
> 3. 全部启用（默认）
> 4. 手动选择

**问题 9.4 - 环境变量**
> 是否需要配置环境变量？
> 1. 是 - 请输入环境变量（格式: KEY=value，多个换行）
> 2. 否（默认）

---

### 步骤 10: 生成预览和确认

在写入文件之前，展示配置预览：

```
📦 即将生成以下配置：

目录: /path/to/project

📄 文件列表:
├── CLAUDE.md                    (~150 行)
├── .mcp.json                    (2 个服务器)
└── .claude/
    ├── README.md                (~80 行)
    ├── settings.json            (~30 行)
    ├── settings.local.json      (~10 行)
    ├── rules/
    │   ├── code-style.md        (~60 行)
    │   ├── testing.md           (~50 行)
    │   └── api-design.md        (~70 行) [paths: src/api/**]
    ├── skills/
    │   └── review-pr/SKILL.md   (~70 行)
    ├── agents/
    │   └── test-writer.md       (~90 行)
    └── hooks/
        └── pre-tool-use.sh      (~50 行)

📊 统计:
- 文件数: 11
- 预计行数: ~700 行
- 主要功能: Rules(3), Skills(1), Agents(1), Hooks(1), MCP(2)
```

**问题 10.1 - 确认生成**
> 确认生成以上配置？
> 1. ✅ 确认生成
> 2. 👁️ 预览具体内容
> 3. ✏️ 修改配置
> 4. ❌ 取消

---

### 步骤 11: 生成文件

确认后，按以下顺序生成文件：

1. **创建目录结构**
   ```bash
   mkdir -p .claude/{rules,skills,agents,hooks}
   ```

2. **生成 CLAUDE.md**（使用项目类型模板）

3. **生成 .claude/README.md**（说明文档）

4. **生成 .claude/settings.json**

5. **生成 .claude/settings.local.json**

6. **生成 Rules 文件**

7. **生成 Skills 目录和文件**

8. **生成 Agents 文件**

9. **生成 Hooks 脚本**

10. **生成 .mcp.json**（如果需要）

11. **更新 .gitignore**（添加 `settings.local.json`）

---

### 步骤 12: 完成报告

生成完成后，输出：

```
✅ Claude Code 配置生成完成！

📂 生成的文件:
   /path/to/project/
   ├── CLAUDE.md ✓
   ├── .mcp.json ✓
   └── .claude/
       ├── README.md ✓
       ├── settings.json ✓
       ├── settings.local.json ✓
       ├── rules/ (3 个规则)
       ├── skills/ (1 个技能)
       ├── agents/ (1 个 agent)
       └── hooks/ (1 个 hook)

📝 后续步骤:
1. 编辑 settings.local.json 填入敏感信息（API 密钥等）
2. 查看 .claude/README.md 了解配置详情
3. 根据需要调整 rules/ 中的规则
4. 运行 Claude Code 开始使用！

⚠️ 注意:
- settings.local.json 已添加到 .gitignore
- MCP 服务器需要在 Claude Code 中运行 /mcp 进行认证

📚 参考文档:
- Claude Code 文档: https://code.claude.com/docs
- Rules 说明: https://code.claude.com/docs/en/memory#organize-rules-with-clauderules
- Skills 说明: https://code.claude.com/docs/en/skills
```

---

## 项目类型模板

### Web Frontend 模板

```markdown
# {项目名称}

## 项目概述

{项目描述}

## 技术栈

- **语言**: {语言}
- **框架**: {框架}
- **构建工具**: {构建工具}
- **测试**: {测试框架}
- **包管理**: {包管理器}

## 目录结构

```
{项目}/
├── src/
│   ├── components/     # UI 组件
│   ├── pages/          # 页面
│   ├── hooks/          # 自定义 Hooks
│   ├── utils/          # 工具函数
│   ├── styles/         # 样式文件
│   └── types/          # TypeScript 类型
├── public/             # 静态资源
└── tests/              # 测试文件
```

## 开发命令

| 操作 | 命令 |
|------|------|
| 开发 | `{dev_cmd}` |
| 构建 | `{build_cmd}` |
| 测试 | `{test_cmd}` |
| Lint | `{lint_cmd}` |

## 组件规范

- 组件文件使用 PascalCase
- 样式使用 CSS Modules 或 Tailwind
- Props 必须有 TypeScript 类型定义
- 复杂组件必须编写 Storybook

## 状态管理

{状态管理方案说明}
```

### Web Backend 模板

```markdown
# {项目名称}

## 项目概述

{项目描述}

## 技术栈

- **语言**: {语言}
- **框架**: {框架}
- **数据库**: {数据库}
- **ORM**: {ORM}
- **测试**: {测试框架}

## 目录结构

```
{项目}/
├── src/
│   ├── controllers/    # 控制器
│   ├── services/       # 业务逻辑
│   ├── repositories/   # 数据访问
│   ├── middleware/     # 中间件
│   ├── routes/         # 路由
│   ├── models/         # 数据模型
│   └── utils/          # 工具
├── tests/
│   ├── unit/           # 单元测试
│   └── integration/    # 集成测试
└── migrations/         # 数据库迁移
```

## API 规范

- RESTful 设计
- 统一响应格式
- 版本控制: /api/v1/

## 开发命令

| 操作 | 命令 |
|------|------|
| 开发 | `{dev_cmd}` |
| 构建 | `{build_cmd}` |
| 测试 | `{test_cmd}` |
| 迁移 | `{migrate_cmd}` |
```

### CLI Tool 模板

```markdown
# {项目名称}

## 项目概述

{项目描述}

## 技术栈

- **语言**: {语言}
- **运行时**: {运行时}
- **CLI 框架**: {框架}

## 目录结构

```
{项目}/
├── src/
│   ├── commands/       # 命令处理
│   ├── utils/          # 工具函数
│   └── index.ts        # 入口
├── tests/
└── README.md
```

## 命令规范

- 主命令: `{cli_name}`
- 子命令使用 kebab-case
- 提供 --help 文档
- 支持 --version

## 开发命令

| 操作 | 命令 |
|------|------|
| 开发 | `{dev_cmd}` |
| 构建 | `{build_cmd}` |
| 测试 | `{test_cmd}` |
| 本地安装 | `{install_cmd}` |
```

### Library 模板

```markdown
# {项目名称}

## 项目概述

{项目描述}

## 技术栈

- **语言**: {语言}
- **构建工具**: {构建工具}
- **测试**: {测试框架}

## 目录结构

```
{项目}/
├── src/
│   ├── index.ts        # 主入口
│   ├── {module}/       # 模块
│   └── utils/          # 工具
├── tests/
├── docs/
└── examples/
```

## API 设计原则

- 简洁一致的 API
- 完善的 TypeScript 类型
- 详细的 JSDoc 注释
- 向后兼容

## 开发命令

| 操作 | 命令 |
|------|------|
| 开发 | `{dev_cmd}` |
| 构建 | `{build_cmd}` |
| 测试 | `{test_cmd}` |
| 文档 | `{docs_cmd}` |
```

---

## Rules 模板

### code-style.md（通用规则）

```markdown
# 代码风格规范

所有代码必须遵循以下规范：

## 命名约定

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | kebab-case | `user-service.ts` |
| 类名 | PascalCase | `UserService` |
| 函数/变量 | camelCase | `getUserById` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |

## 代码格式

- 缩进: {indent} 空格
- 最大行宽: {line_width} 字符
- 引号: 单引号
- 分号: {semicolon}

## 导入顺序

1. 标准库/内置模块
2. 第三方依赖
3. 项目内部模块
4. 类型导入

## 注释规范

- 公共 API 必须有文档注释
- 复杂逻辑必须有说明
- 避免无用的注释
```

### api-design.md（路径特定规则）

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "src/controllers/**/*.ts"
  - "src/routes/**/*.ts"
---

# API 开发规范

处理 API 相关代码时必须遵循：

## RESTful 设计

- 使用名词复数: `/users`, `/orders`
- 正确使用 HTTP 方法
- 版本控制: `/api/v1/`

## 响应格式

### 成功
```json
{
  "success": true,
  "data": { ... }
}
```

### 错误
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

## 必须包含

- [ ] 请求验证
- [ ] 错误处理
- [ ] 日志记录
- [ ] API 文档
```

### frontend-components.md（路径特定规则）

```markdown
---
paths:
  - "src/components/**/*.tsx"
  - "src/pages/**/*.tsx"
---

# 前端组件规范

## 组件结构

1. 导入语句
2. 类型定义
3. 样式导入
4. 组件定义
5. 导出

## 命名约定

- 组件文件: `PascalCase.tsx`
- 样式文件: `Component.module.css`
- 测试文件: `Component.test.tsx`
- Story: `Component.stories.tsx`

## 必须包含

- [ ] TypeScript 类型
- [ ] Props 验证
- [ ] 默认值
- [ ] 单元测试

## 禁止

- 内联样式（除非动态）
- 硬编码文本（使用 i18n）
- 直接 DOM 操作
```

### testing.md（通用规则）

```markdown
# 测试规范

## 测试策略

- 单元测试: 独立函数和类
- 集成测试: API 和服务交互
- E2E 测试: 完整用户流程

## 测试结构

```typescript
describe('ModuleName', () => {
  describe('functionName', () => {
    it('should ... when ...', () => {
      // Arrange
      // Act
      // Assert
    });
  });
});
```

## 测试原则

- AAA 模式: Arrange-Act-Assert
- 一个测试一个断言
- 测试名称描述行为
- Mock 外部依赖

## 覆盖率要求

- 行覆盖率: >= 80%
- 分支覆盖率: >= 70%
- 关键路径: 100%
```

### security.md（通用规则）

```markdown
# 安全规范

## 认证与授权

- 使用安全的认证机制
- Token 有效期合理设置
- 敏感操作二次验证

## 输入验证

- 所有输入必须验证
- 使用参数化查询
- 输出进行转义

## 敏感数据

### 禁止

- 日志中输出敏感信息
- 硬编码密钥
- 提交 .env 文件

### 必须

- 使用环境变量
- 加密存储
- 定期轮换密钥

## 依赖安全

- 定期运行安全审计
- 及时更新有漏洞的依赖
```

---

## Skills 模板

### review-pr/SKILL.md

```yaml
---
name: review-pr
description: 审查 Pull Request 代码变更，检查代码质量、安全问题和最佳实践。
argument-hint: [pr-number]
---

# PR 代码审查

## 审查流程

1. 获取 PR 变更
2. 逐文件审查
3. 检查代码质量、安全、性能
4. 生成审查报告

## 检查清单

### 代码质量
- [ ] 代码清晰易懂
- [ ] 命名有意义
- [ ] 无重复代码
- [ ] 遵循规范

### 安全
- [ ] 输入验证
- [ ] 敏感数据处理
- [ ] 无注入风险

### 性能
- [ ] 无 N+1 查询
- [ ] 无不必要循环

### 测试
- [ ] 有测试覆盖
- [ ] 边界条件覆盖

## 输出格式

[生成审查报告，包含问题等级和建议]
```

---

## Agents 模板

### test-writer.md

```yaml
---
name: test-writer
description: 为代码编写单元测试和集成测试的专家 Agent。
tools: Read, Grep, Glob, Write, Edit, Bash
model: sonnet
---

# 测试编写 Agent

## 工作流程

1. 分析目标代码
2. 设计测试用例
3. 编写测试代码
4. 运行验证

## 测试原则

- AAA 模式
- 一个测试一个断言
- Mock 外部依赖
- 边界条件覆盖

## 输出

- 测试文件
- 运行结果
- 覆盖率报告
```

---

## Hooks 模板

### pre-tool-use.sh

```bash
#!/bin/bash
# PreToolUse Hook: 安全检查

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 危险命令检查
DANGEROUS=(
    "rm -rf /"
    "rm -rf /*"
    "curl.*|.*bash"
)

for pattern in "${DANGEROUS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        jq -n "{
            hookSpecificOutput: {
                hookEventName: \"PreToolUse\",
                permissionDecision: \"deny\",
                permissionDecisionReason: \"禁止危险命令\"
            }
        }"
        exit 0
    fi
done

exit 0
```

---

## .claude/README.md 模板

```markdown
# .claude 配置目录

本目录包含 Claude Code 的项目配置。

## 目录结构

```
.claude/
├── settings.json        # 项目设置（提交到 Git）
├── settings.local.json  # 本地设置（不提交，存放敏感信息）
├── rules/               # 模块化规则
├── skills/              # 自定义技能
├── agents/              # 自定义 Agent
└── hooks/               # 生命周期钩子
```

## 配置说明

### settings.json

项目级设置，包含：
- 权限配置
- 环境变量
- Hook 配置

### settings.local.json

本地设置，**不要提交到 Git**：
- API 密钥
- 数据库连接字符串
- 其他敏感信息

### rules/

模块化规则文件：
- 无 `paths` 字段: 启动时加载
- 有 `paths` 字段: 处理匹配文件时加载

### skills/

自定义技能，可通过 `/skill-name` 调用。

### agents/

自定义 Subagent，用于特定任务的代理。

### hooks/

生命周期钩子脚本：
- `pre-tool-use.sh`: 工具执行前
- `post-tool-use.sh`: 工具执行后

## 使用方法

1. 在 Claude Code 中打开项目
2. 配置会自动加载
3. 使用 `/help` 查看可用命令

## 文档

- [Claude Code 文档](https://code.claude.com/docs)
- [Memory 和 Rules](https://code.claude.com/docs/en/memory)
- [Skills](https://code.claude.com/docs/en/skills)
- [Agents](https://code.claude.com/docs/en/sub-agents)
- [Hooks](https://code.claude.com/docs/en/hooks)
```

---

## .gitignore 更新

生成后自动检查并添加：

```gitignore
# Claude Code local settings
.claude/settings.local.json

# Optional: also ignore if you don't want to share
# .claude/agents/
# .claude/skills/
```

---

## ⚡ 一键部署方案

除了交互式生成，还支持以下快速部署方式：

### 方式 1: 预设模板快速部署

使用预设模板，无需交互，一键生成配置：

**Web Frontend 项目**
```
/claude-code-setup --template frontend
```

**Web Backend 项目**
```
/claude-code-setup --template backend
```

**CLI Tool 项目**
```
/claude-code-setup --template cli
```

**Library 项目**
```
/claude-code-setup --template library
```

**Minimal 项目**（仅基础配置）
```
/claude-code-setup --template minimal
```

---

### 方式 2: 命令行参数部署

通过参数指定所有配置，完全自动化：

```bash
# 示例：创建 Backend 项目
/claude-code-setup \
  --path /path/to/project \
  --name "my-api" \
  --type backend \
  --language typescript \
  --framework "Express,Prisma" \
  --rules code-style,testing,security,api-design \
  --skills review-pr \
  --agents test-writer \
  --hooks pre-tool-use \
  --mcp github,postgres \
  --yes
```

**参数说明**:

| 参数 | 说明 | 示例 |
|------|------|------|
| `--path` | 目标路径 | `/home/user/my-project` |
| `--name` | 项目名称 | `my-api` |
| `--type` | 项目类型 | `frontend/backend/cli/library/mobile/desktop` |
| `--language` | 编程语言 | `typescript/javascript/python/go/rust/java` |
| `--framework` | 框架（逗号分隔） | `React,Next.js` |
| `--rules` | 规则文件（逗号分隔） | `code-style,testing,security` |
| `--skills` | 技能（逗号分隔） | `review-pr,run-tests` |
| `--agents` | Agent（逗号分隔） | `test-writer,code-reviewer` |
| `--hooks` | Hook（逗号分隔） | `pre-tool-use,post-tool-use` |
| `--mcp` | MCP 服务器（逗号分隔） | `github,postgres,slack` |
| `--permission-mode` | 权限模式 | `default/acceptEdits/plan/dontAsk` |
| `--yes` | 跳过确认 | - |

---

### 方式 3: JSON 配置文件部署

通过 JSON 配置文件定义所有设置：

```bash
/claude-code-setup --config setup.json
```

**setup.json 示例**:

```json
{
  "project": {
    "name": "my-api-server",
    "type": "backend",
    "language": "typescript",
    "framework": ["Express", "Prisma"],
    "description": "企业级 REST API 服务"
  },
  "claudeMd": {
    "includeTechStack": true,
    "includeDirectoryStructure": true,
    "includeCommands": true,
    "includeCodingStyle": true,
    "includeTesting": true,
    "includeGitConvention": true
  },
  "rules": {
    "enabled": true,
    "files": ["code-style", "testing", "security", "api-design"],
    "userLevel": false
  },
  "skills": {
    "enabled": true,
    "files": ["review-pr", "run-tests"]
  },
  "agents": {
    "enabled": true,
    "files": ["test-writer"],
    "defaultModel": "sonnet"
  },
  "hooks": {
    "enabled": true,
    "types": ["PreToolUse"],
    "preToolUse": {
      "blockDangerousCommands": true,
      "protectSensitiveFiles": true
    }
  },
  "mcp": {
    "enabled": true,
    "servers": ["github", "postgres"],
    "scope": "project"
  },
  "settings": {
    "permissionMode": "default",
    "preApproveTools": ["npm", "git", "Read"],
    "denySensitiveFiles": true
  }
}
```

---

### 方式 4: 远程模板部署

从 GitHub/GitLab 仓库克隆预配置模板：

```bash
# 从模板仓库部署
/claude-code-setup --from https://github.com/user/claude-template-backend

# 从本地模板部署
/claude-code-setup --from /path/to/template
```

---

## 📦 预设模板详情

### Frontend 模板

适用于 React/Vue/Angular/Svelte 等前端项目。

**自动包含**:
- CLAUDE.md（前端配置）
- Rules: code-style, testing, frontend-components（带 paths）
- Skills: review-pr, create-component
- Agents: test-writer
- Hooks: pre-tool-use
- MCP: GitHub

**settings.json**:
```json
{
  "permissions": {
    "allow": ["Bash(npm *)", "Bash(pnpm *)", "Bash(git *)", "Read(**)"],
    "deny": ["Read(.env)", "Read(.env.*)"],
    "defaultMode": "default"
  },
  "env": {
    "NODE_ENV": "development"
  }
}
```

---

### Backend 模板

适用于 Node.js/Python/Go/Java 等后端 API 项目。

**自动包含**:
- CLAUDE.md（后端配置）
- Rules: code-style, testing, security, api-design（带 paths）
- Skills: review-pr, create-api
- Agents: test-writer, code-reviewer
- Hooks: pre-tool-use（增强安全检查）
- MCP: GitHub, PostgreSQL

**settings.json**:
```json
{
  "permissions": {
    "allow": [
      "Bash(npm *)", "Bash(pnpm *)", "Bash(git *)",
      "Bash(npx prisma *)", "Read(**)"
    ],
    "deny": [
      "Read(.env)", "Read(.env.*)", "Read(**/secrets/**)",
      "Read(**/*.pem)", "Read(**/*.key)"
    ],
    "defaultMode": "default"
  },
  "env": {
    "NODE_ENV": "development"
  }
}
```

---

### CLI 模板

适用于命令行工具项目。

**自动包含**:
- CLAUDE.md（CLI 配置）
- Rules: code-style, testing, cli-commands（带 paths）
- Skills: review-pr
- Agents: test-writer
- Hooks: pre-tool-use
- MCP: GitHub

---

### Library 模板

适用于库/包项目。

**自动包含**:
- CLAUDE.md（库配置）
- Rules: code-style, testing
- Skills: review-pr, release
- Agents: test-writer, doc-writer
- Hooks: pre-tool-use
- MCP: GitHub

---

### Minimal 模板

最小配置，仅包含必要文件。

**自动包含**:
- CLAUDE.md（基础配置）
- settings.json（基础权限）

---

## 🔄 部署后操作

生成完成后，自动执行以下操作：

### 1. 验证配置

```bash
# 验证 JSON 格式
cat .claude/settings.json | jq .
```

### 2. 更新 .gitignore

自动检测并添加：

```gitignore
# Claude Code local settings (auto-added by claude-code-setup)
.claude/settings.local.json
```

### 3. 设置 Hook 权限

```bash
chmod +x .claude/hooks/*.sh
```

### 4. 输出后续步骤

```
✅ 配置生成完成！

📝 后续步骤:
1. 编辑 .claude/settings.local.json 填入敏感信息
2. 运行 claude 启动 Claude Code
3. 使用 /mcp 配置 MCP 服务器认证

📚 文档:
- 配置说明: .claude/README.md
- 官方文档: https://code.claude.com/docs
```

---

## 注意事项

1. **不覆盖已有文件**: 除非用户明确确认或使用 `--force`
2. **敏感信息**: 始终放入 settings.local.json
3. **路径验证**: 确保目标目录存在
4. **错误处理**: 提供清晰的错误信息
5. **回滚支持**: 如果生成失败，清理已创建的文件
6. **配置验证**: 生成后自动验证 JSON 格式
