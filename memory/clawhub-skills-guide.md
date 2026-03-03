# ClawHub Skills 实战指南

> 🔗 官网: https://clawhub.com  
> 📅 整理时间: 2026-02-28  
> ✅ 已实际上手验证

---

## 一、什么是 ClawHub？

ClawHub 是一个 **Agent Skills 技能市场**，可以按需发现、安装和使用各种 AI 助手技能模块。类似 npm 之于 Node.js，ClawHub 让 AI 助手能够扩展能力边界。

---

## 二、安装与配置

```bash
# 全局安装 ClawHub CLI
npm i -g clawhub

# 登录（发布技能需要）
clawhub login
clawhub whoami
```

---

## 三、核心命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `search` | 搜索技能 | `clawhub search "github"` |
| `install` | 安装技能 | `clawhub install my-skill` |
| `list` | 列出已安装技能 | `clawhub list` |
| `update` | 更新技能 | `clawhub update my-skill` |
| `publish` | 发布技能 | `clawhub publish ./my-skill` |

---

## 四、实际操作演示

### 4.1 搜索技能

```bash
# 搜索 GitHub 相关技能
$ clawhub search "github"
- Searching
github  Github  (3.776)           ← 最高评分
openclaw-github-assistant  OpenClaw GitHub Assistant  (3.605)
github-cli  Github Cli  (3.475)
github-mcp  GitHub MCP Server  (3.442)

# 搜索图像处理技能
$ clawhub search "image"
antigravity-image-gen  Antigravity Image Generator  (3.567)
image-cog  image-cog  (3.549)
gemini-image-simple  Gemini Image Simple  (3.497)

# 搜索数据分析技能
$ clawhub search "data"
data-analyst  Data Analyst  (3.512)
data-analysis  Data Analysis  (3.497)
data-model-designer  Data Model Designer  (3.463)
```

### 4.2 查看已安装技能

```bash
$ clawhub list
code  1.0.4
test-runner  1.0.0
```

### 4.3 安装技能

```bash
# 常规安装
$ clawhub install github

# 指定版本
$ clawhub install my-skill --version 1.2.3

# 强制安装（被标记为可疑的技能）
$ clawhub install data-analyst --force
```

⚠️ **注意**：部分技能会被 VirusTotal 标记为可疑，需要 `--force` 参数：
```
⚠️  Warning: "data-analyst" is flagged as suspicious by VirusTotal Code Insight.
   This skill may contain risky patterns (crypto keys, external APIs, eval, etc.)
```

---

## 五、热门 Skills 分类

### 🔧 开发工具类

| Skill | 评分 | 用途 |
|-------|------|------|
| `github` | ⭐ 3.78 | GitHub 操作 |
| `openclaw-github-assistant` | ⭐ 3.61 | GitHub 助手 |
| `github-cli` | ⭐ 3.48 | GitHub CLI 封装 |
| `code` | ✅ 已安装 | 代码工作流 |
| `test-runner` | ✅ 已安装 | 测试运行器 |

### 🎨 图像处理类

| Skill | 评分 | 用途 |
|-------|------|------|
| `antigravity-image-gen` | ⭐ 3.57 | AI 图像生成 |
| `image-edit` | ⭐ 3.45 | 图像编辑 |
| `gemini-image-simple` | ⭐ 3.50 | Gemini 图像 |
| `qwen-image` | ⭐ 3.49 | 通义图像生成 |

### 🌐 Web 相关类

| Skill | 评分 | 用途 |
|-------|------|------|
| `web-deploy-github` | ⭐ 3.48 | GitHub Pages 部署 |
| `web-pilot` | ⭐ 3.41 | Web 自动化 |
| `ai-web-automation` | ⭐ 3.38 | AI Web 自动化 |

### 📊 数据分析类

| Skill | 评分 | 用途 |
|-------|------|------|
| `data-analyst` | ⭐ 3.51 | 数据分析 |
| `data-model-designer` | ⭐ 3.46 | 数据模型设计 |
| `data-lineage-tracker` | ⭐ 3.43 | 数据血缘追踪 |

### 🎮 3D/游戏/渲染类

| Skill | 评分 | 用途 |
|-------|------|------|
| `3d-cog` | ⭐ 3.33 | 3D COG 处理 |
| `tex-render` | ⭐ 3.34 | TeX 渲染 |
| `openclaw-godot-skill` | ⭐ 0.91 | Godot 游戏引擎 |
| `threejs` | ⭐ 0.93 | Three.js 3D |

---

## 六、Code Skill 实战案例

### 6.1 Skill 结构

Code Skill 提供了完整的编码工作流指导：

```
code/
├── SKILL.md        # 主文档
├── planning.md     # 任务规划
├── execution.md    # 执行流程
├── verification.md # 验证方法
└── memory.md       # 用户偏好
```

### 6.2 工作流程

```
Request → Plan → Execute → Verify → Deliver
```

### 6.3 实战演示：创建 OpenGL 三角形

**步骤 1：规划**（按 Code Skill 指导）

```
Step 1: 创建基础窗口和三角形渲染
- Output: hello_triangle.cpp 可执行文件
- Test: 运行程序，显示绿色三角形
```

**步骤 2：实现代码**

创建了 `hello_triangle.cpp`，包含：
- GLFW 窗口初始化
- OpenGL 3.3 Core Profile 配置
- 顶点/片段着色器编译
- VAO/VBO 创建和绑定
- 渲染循环

**步骤 3：编译**

```bash
$ cd demos/skill-demo && mkdir -p build && cd build
$ cmake ..
$ make
[ 50%] Building CXX object CMakeFiles/hello_triangle.dir/hello_triangle.cpp.o
[100%] Linking CXX executable hello_triangle
[100%] Built target hello_triangle
```

**步骤 4：验证**

```bash
$ DISPLAY=:99 ./hello_triangle
OpenGL 版本: 4.5 (Core Profile) Mesa 25.2.8-0ubuntu0.24.04.1
GLSL 版本: 4.50

✅ 初始化成功！开始渲染...
按 ESC 键退出
```

截图验证：✅ 显示深蓝背景上的翠绿色三角形

---

## 七、最佳实践

1. **按需安装**: 先 `search` 找到最合适的 skill，再 `install`
2. **版本控制**: 生产环境建议指定 `--version`
3. **定期更新**: 使用 `update --all` 保持技能最新
4. **安全意识**: 被标记可疑的技能要审查代码后再使用
5. **贡献社区**: 开发有用的 skill 可以 `publish` 分享

---

## 八、注意事项

- 默认注册表: https://clawhub.com
- 安装目录: `./skills`
- 需要 Node.js 环境
- 发布需要先 `clawhub login`
- 有 API 速率限制，批量操作需间隔

---

## 九、常见问题

### Q: 安装时提示 Rate limit exceeded？
A: ClawHub 有 API 速率限制，等待几分钟后重试。

### Q: 技能被标记为 suspicious？
A: 使用 `--force` 参数强制安装，但建议先审查代码。

### Q: 如何查看技能的详细内容？
A: 安装后查看 `./skills/<skill-name>/SKILL.md`

---

*文档由 Glint 🔺 整理，包含实际操作验证*
