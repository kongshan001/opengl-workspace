# OpenGL 工作空间

图形精灵 Glint 的开发工作空间，专注于 OpenGL / 图形渲染 / 游戏引擎相关的开发工作。

## 项目结构

```
opengl-workspace/
├── AGENTS.md           # Agent 角色定义
├── SOUL.md             # 图形精灵 Glint 人设
├── USER.md             # 用户偏好
├── TOOLS.md            # 本地工具配置
├── MEMORY.md           # 长期记忆
├── memory/             # 每日日志
└── github-analyzer/    # GitHub Project Analyzer 工具
```

## GitHub Project Analyzer

一键式开源项目分析工具，将 GitHub 项目转化为多模态内容资产。

### 工作流程

```
GitHub URL → 数据采集 → 深度分析 → 文档生成 → 可视化图表 → 视频内容
```

### 使用方法

```bash
# 数据采集
cd github-analyzer
./scripts/collector.sh https://github.com/owner/repo

# 或在 OpenClaw 中说
"分析 https://github.com/vercel/next.js"
```

### 输出内容

- 📊 完整调研报告 (Markdown)
- 🖼️ 架构图、平台图 (PNG)
- 🎬 视频内容 (MP4 + 配音 + 字幕)

### 演示项目

已分析 **openclaw/openclaw** (257K stars)：
- [完整报告](github-analyzer/output/docs/full_report.md)
- [架构图](github-analyzer/output/images/architecture.png)
- [视频](github-analyzer/output/video/output_with_audio.mp4)

## 技能

- [Self-Improving](memory/2026-03-04-self-improving-research.md) - 自我学习与反思
- [GitHub Project Analyzer](github-analyzer/) - 项目分析工具

## 开发环境

- 系统: Linux (Ubuntu 24.04)
- 编译器: GCC 13.3.0
- 构建工具: CMake 3.28
- OpenGL: 3.3 Core Profile

## 联系方式

- 飞书私聊
- GitHub: https://github.com/kongshan001/opengl-workspace

---

*图形精灵 Glint 🔺 - 从三角形开始，向世界渲染色彩*
