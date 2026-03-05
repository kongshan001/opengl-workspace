# .claude 配置目录

本目录包含 Claude Code 的项目配置，用于自定义 Claude 在本项目中的行为。

> 📅 生成时间: 2026-03-05
> 🛠️ 生成工具: claude-code-setup skill

---

## 📂 目录结构

```
.claude/
├── settings.json        # 项目设置（提交到 Git）
├── settings.local.json  # 本地设置（不提交，存放敏感信息）
├── rules/               # 模块化规则
│   ├── code-style.md    # 代码风格规范
│   ├── testing.md       # 测试规范
│   ├── security.md      # 安全规范
│   └── api-design.md    # API 设计规范（条件加载）
├── skills/              # 自定义技能
│   └── review-pr/       # PR 审查技能
├── agents/              # 自定义 Agent
│   └── test-writer.md   # 测试编写 Agent
└── hooks/               # 生命周期钩子
    └── pre-tool-use.sh  # 工具执行前安全检查
```

---

## ⚙️ 配置说明

### settings.json

项目级设置，包含：

- **权限配置**: 允许/禁止的工具操作
- **环境变量**: 开发环境变量
- **Hook 配置**: 生命周期钩子绑定

### settings.local.json

本地设置，**不要提交到 Git**！

存放：
- API 密钥
- 数据库连接字符串
- JWT Secret
- 其他敏感信息

### rules/

模块化规则文件，按加载方式分为：

| 类型 | 加载时机 | 示例 |
|------|----------|------|
| 通用规则 | 会话启动时 | code-style.md, testing.md |
| 路径特定规则 | 处理匹配文件时 | api-design.md |

路径特定规则使用 `paths` frontmatter 指定匹配模式：

```yaml
---
paths:
  - "src/api/**/*.ts"
---
```

### skills/

自定义技能，可通过 `/skill-name` 调用：

| Skill | 调用方式 | 说明 |
|-------|----------|------|
| review-pr | `/review-pr 123` | 审查 PR 代码 |

### agents/

自定义 Subagent，用于特定任务的代理：

| Agent | 工具 | 说明 |
|-------|------|------|
| test-writer | Read, Write, Edit, Bash | 编写测试用例 |

### hooks/

生命周期钩子脚本：

| Hook | 触发时机 | 功能 |
|------|----------|------|
| pre-tool-use.sh | 工具执行前 | 危险命令拦截、敏感文件保护 |

---

## 🚀 使用方法

1. **配置敏感信息**
   ```bash
   # 编辑 settings.local.json，填入真实值
   vim .claude/settings.local.json
   ```

2. **在 Claude Code 中打开项目**
   ```bash
   cd /path/to/project
   claude
   ```

3. **使用自定义技能**
   ```
   /review-pr 123
   ```

4. **委托任务给 Agent**
   ```
   让 test-writer agent 为 src/services/user.ts 编写测试
   ```

---

## 📚 文档

- [Claude Code 官方文档](https://code.claude.com/docs)
- [Memory 和 Rules](https://code.claude.com/docs/en/memory)
- [Skills](https://code.claude.com/docs/en/skills)
- [Agents](https://code.claude.com/docs/en/sub-agents)
- [Hooks](https://code.claude.com/docs/en/hooks)
- [MCP](https://code.claude.com/docs/en/mcp)

---

## 🔧 自定义

### 添加新规则

1. 在 `rules/` 目录创建 `.md` 文件
2. 添加 YAML frontmatter（如需条件加载）
3. 编写规则内容

### 添加新技能

1. 在 `skills/` 目录创建子目录
2. 创建 `SKILL.md` 文件
3. 添加 frontmatter 和内容

### 添加新 Agent

1. 在 `agents/` 目录创建 `.md` 文件
2. 配置 frontmatter（tools, model 等）
3. 编写 Agent 系统提示

---

## ⚠️ 注意事项

1. **不要提交 settings.local.json** - 已添加到 .gitignore
2. **规则文件保持在 200 行以内** - 过长会影响上下文
3. **Hook 脚本需要有执行权限** - `chmod +x .claude/hooks/*.sh`
4. **MCP 服务器需要认证** - 首次使用运行 `/mcp` 进行认证
