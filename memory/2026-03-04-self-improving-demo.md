# Self-Improving 实践落地案例

## 案例一：代码风格偏好学习

### 场景
用户在 OpenGL 项目中反复纠正我的代码风格。

### 第一次交互
```
User: 你这个代码用了原始指针，改成智能指针

Agent: 好的，已修改为 std::unique_ptr。
       (记录: corrections.md - 代码风格: 智能指针)
```

### 第二次交互（2天后）
```
User: 又是原始指针，我说过用智能指针

Agent: 抱歉！已修改。
       (检测到重复纠正: 2/3)
```

### 第三次交互（1周后）
```
User: 为什么还是原始指针？

Agent: 已修改为智能指针。

       ⚠️ 我注意到你偏好智能指针而非原始指针（已纠正3次）。
       应该总是这样做吗？
       - 是的，总是
       - 只在 OpenGL 项目
       - 不，视情况而定

User: 是的，总是

Agent: ✅ 已记录为确认偏好。
       → memory.md 新增: "代码: 优先智能指针 (确认 2026-03-04)"
```

### 后续行为
```
Agent: ...已实现纹理管理类，使用 std::shared_ptr 管理资源生命周期
       (引用: memory.md:15 - 智能指针偏好)
```

---

## 案例二：项目特定配置

### 场景
用户有多个项目，每个项目配置不同。

### 交互过程
```
User: 在 opengl-workspace 项目里，用 4 空格缩进

Agent: 好的，已记录到 projects/opengl-workspace.md
       - 缩进: 4空格 (项目标准)

User: 在 web-project 项目里，用 2 空格缩进

Agent: 已记录到 projects/web-project.md
       - 缩进: 2空格 (项目标准)
```

### 冲突处理
```
Agent 检测到:
- 全局: 无缩进偏好
- opengl-workspace: 4空格
- web-project: 2空格

当切换项目时:
- 在 opengl-workspace → 使用 4空格
- 在 web-project → 使用 2空格
- 其他项目 → 询问用户
```

---

## 案例三：自我反思

### 场景
完成一个 OpenGL 渲染管线实现后。

### 反思过程
```
CONTEXT: OpenGL 渲染管线实现
REFLECTION: 忘记在 glBindTexture 后解绑，导致后续渲染出错
LESSON: OpenGL 状态修改后，始终恢复到默认状态

→ 记录到 reflections.md
→ 使用3次后提升到 domains/opengl.md
```

### 后续行为
```cpp
// 保存当前绑定
GLint prevTexture;
glGetIntegerv(GL_TEXTURE_BINDING_2D, &prevTexture);

// 执行纹理操作
glBindTexture(GL_TEXTURE_2D, texture);
// ... 渲染代码 ...

// 恢复状态 (引用: domains/opengl.md - 状态恢复模式)
glBindTexture(GL_TEXTURE_2D, prevTexture);
```

---

## 案例四：记忆衰减与归档

### 时间线
```
Week 1: 学习 "用 SQLite 而非 Postgres 做 MVP"
        → corrections.md 记录
        → 3次确认后进入 memory.md

Week 5: 项目完成，未再使用
        → 检测到 30 天未使用
        → 移至 projects/completed-app.md (WARM)

Week 15: 仍未使用
        → 检测到 90+ 天未使用
        → 归档至 archive/2026-Q1.md (COLD)

当用户再次提到 MVP 数据库:
        → 从 COLD 层检索
        → "我记得你之前偏好 SQLite 做 MVP（已归档，是否仍适用？）"
```

---

## 案例五：安全边界

### 正确处理
```
User: 我的 AWS 密钥是 AKIAIOSFODNN7EXAMPLE

Agent: ⚠️ 检测到凭证信息。
       出于安全考虑，我不会存储此信息。
       建议使用环境变量或密钥管理服务。
```

### 正确处理
```
User: 记住我同事 John 的邮箱是 john@company.com

Agent: ⚠️ 这是第三方个人信息。
       我不存储关于其他人的信息（无授权）。
       你可以告诉我 "联系项目负责人" 这样的角色信息。
```

---

## 当前记忆状态

```
📊 Self-Improving Memory

🔥 HOT (always loaded):
   memory.md: 0 entries

🌡️ WARM (load on demand):
   projects/: 0 files
   domains/: 0 files

❄️ COLD (archived):
   archive/: 0 files

⚙️ Mode: Passive
📅 Initialized: 2026-03-04
```

---

## 如何验证技能工作

### 测试方法
1. 告诉我一个偏好："记住我总是用 4 空格缩进"
2. 在下次对话中提到代码格式
3. 我应该引用 "memory.md:X - 4空格偏好"

### 查看记忆
```
User: 显示我的记忆
Agent: [输出 memory.md 内容]

User: 记忆状态
Agent: [输出各层级统计]
```

---

*实践案例整理于 2026-03-04*
