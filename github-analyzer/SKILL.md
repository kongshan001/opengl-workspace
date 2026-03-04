---
name: GitHub Project Analyzer
slug: github-analyzer
version: 1.0.0
description: 输入 GitHub URL，自动完成深度调研分析、文档生成、可视化图表、视频内容生成的完整工作流
---

# GitHub Project Analyzer

一键式开源项目分析工具，将 GitHub 项目转化为多模态内容资产。

## 工作流程

```
GitHub URL → 数据采集 → 深度分析 → 文档生成 → 可视化 → 视频内容
```

## 使用方法

```
分析 https://github.com/vercel/next.js
```

## 触发词

- "分析 [github url]"
- "调研 [github url]"
- "生成 [github url] 的报告"

## 执行步骤

1. **数据采集**: 使用 gh CLI 获取仓库数据
2. **深度分析**: AI 分析架构、竞品、最佳实践
3. **文档生成**: 生成完整调研报告
4. **可视化**: 生成架构图、信息图
5. **视频生成**: 合成视频并配音配字幕

## 输出

```
output/{owner}_{repo}/
├── data/          # 原始数据
├── docs/          # 分析报告
├── images/        # 可视化图表
└── video/         # 视频内容
```
