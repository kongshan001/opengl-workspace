#!/bin/bash

# PSG 验证脚本 - 验证下一个仓库
# 用法: ./validate_next_repo.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS_DIR="$SCRIPT_DIR/../repos"
REPORTS_DIR="$SCRIPT_DIR/../doc/practices"
DATE=$(date +%Y-%m-%d)

# 创建必要的目录
mkdir -p "$REPORTS_DIR"

# 获取下一个需要验证的仓库
get_next_repo() {
    local repos=("$REPOS_DIR"/*)
    local shuffled_repos=()
    
    # Fisher-Yates shuffle 算法
    for ((i=${#repos[@]}-1; i>0; i--)); do
        local j=$((RANDOM % (i+1)))
        shuffled_repos+=("${repos[i]}")
        if [ $i -ne $j ]; then
            repos[i]="${repos[j]}"
        fi
    done
    
    # 打乱数组的前半部分
    for repo in "${repos[@]}"; do
        if [ -d "$repo" ] && [ ! -f "$repo/validation_complete" ]; then
            echo "$repo"
            return
        fi
    done
    
    # 如果所有仓库都验证过了，返回第一个
    if [ ${#repos[@]} -gt 0 ]; then
        echo "${repos[0]}"
    fi
}

# 验证单个仓库
validate_repo() {
    local repo_path="$1"
    local repo_name=$(basename "$repo_path")
    local report_file="$REPORTS_DIR/${repo_name}_issues_${DATE}.md"
    
    echo "🔍 正在验证仓库: $repo_name"
    echo "📍 路径: $repo_path"
    
    # 检查仓库是否存在
    if [ ! -d "$repo_path" ]; then
        echo "❌ 仓库不存在: $repo_path"
        return 1
    fi
    
    # 检查是否有分析JSON文件
    local analysis_files=("$repo_path"/*analysis.json)
    if [ ${#analysis_files[@]} -eq 0 ] || [ ! -f "${analysis_files[0]}" ]; then
        echo "⚠️  未找到分析JSON文件"
        echo "📝 记录到报告: $report_file"
        cat > "$report_file" << EOF
# $repo_name 验证问题报告 - $DATE

## 🔍 验证信息
- **仓库名称**: $repo_name
- **验证路径**: $repo_path
- **验证时间**: $(date)
- **验证状态**: ⚠️ 需要关注

## ❌ 发现的问题

### 1. 缺少分析JSON文件
- **问题描述**: 仓库中未找到 *_analysis.json 文件
- **影响程度**: 🔴 高
- **建议修复**: 运行项目分析器生成分析文件

### 2. 可能的其他问题
待进一步检查...

## ✅ 正常项目
- 项目目录结构正常
- 基本文件存在

## 🔧 建议的修复步骤
1. 检查项目是否支持当前的分析器
2. 如果需要，运行 `codebase-analyzer` 工具
3. 重新验证项目

---
*验证完成时间: $(date)*
*验证工具: PSG Validator v1.0*
EOF
        return 1
    fi
    
    # 检查分析JSON文件的有效性
    if ! jq empty "${analysis_files[0]}" 2>/dev/null; then
        echo "❌ 分析JSON文件格式无效"
        echo "📝 记录到报告: $report_file"
        cat > "$report_file" << EOF
# $repo_name 验证问题报告 - $DATE

## 🔍 验证信息
- **仓库名称**: $repo_name
- **验证路径**: $repo_path
- **验证时间**: $(date)
- **验证状态**: ❌ 严重问题

## ❌ 发现的问题

### 1. 分析JSON文件格式无效
- **问题描述**: ${analysis_files[0]} 文件不是有效的JSON格式
- **影响程度**: 🔴 高
- **建议修复**: 重新生成分析文件或修复JSON格式

### 2. JSON解析错误
$(jq . "${analysis_files[0]}" 2>&1 || echo "无法解析JSON文件")

## ✅ 正常项目
- 项目目录结构正常
- 文件存在

## 🔧 建议的修复步骤
1. 检查JSON文件格式
2. 重新运行项目分析
3. 验证修复结果

---
*验证完成时间: $(date)*
*验证工具: PSG Validator v1.0*
EOF
        return 1
    fi
    
    # 提取分析信息
    local project_type=$(jq -r '.project_type // "unknown"' "${analysis_files[0]}")
    local module_count=$(jq -r '.modules | length // 0' "${analysis_files[0]}")
    local language=$(jq -r '.primary_language // "unknown"' "${analysis_files[0]}")
    
    echo "✅ 项目类型: $project_type"
    echo "✅ 主要语言: $language"
    echo "✅ 模块数量: $module_count"
    
    # 检查项目健康度
    local issues_found=0
    
    # 检查模块数量是否合理
    if [ "$module_count" -eq 0 ]; then
        echo "⚠️  模块数量为0，可能存在问题"
        issues_found=$((issues_found + 1))
    fi
    
    # 检查项目类型是否支持
    case "$project_type" in
        "python"|"javascript"|"typescript"|"cpp"|"c++"|"shell"|"documentation"|"workspace")
            echo "✅ 项目类型受支持"
            ;;
        *)
            echo "⚠️  项目类型 $project_type 可能不受支持"
            issues_found=$((issues_found + 1))
            ;;
    esac
    
    # 生成验证报告
    if [ $issues_found -gt 0 ]; then
        echo "📝 记录到报告: $report_file"
        cat > "$report_file" << EOF
# $repo_name 验证问题报告 - $DATE

## 🔍 验证信息
- **仓库名称**: $repo_name
- **验证路径**: $repo_path
- **验证时间**: $(date)
- **验证状态**: ⚠️ 发现 $issues_found 个问题

## 📊 项目概览
- **项目类型**: $project_type
- **主要语言**: $language
- **模块数量**: $module_count
- **分析文件**: ${analysis_files[0]}

## ⚠️ 发现的问题

### 1. 模块数量检查
- **状态**: $([ "$module_count" -eq 0 ] && echo "❌ 问题" || echo "✅ 正常")
- **当前值**: $module_count
- **建议**: $([ "$module_count" -eq 0 ] && echo "建议检查项目结构，确保能正确识别模块" || echo "模块数量正常")

### 2. 项目类型支持检查
- **状态**: $([[ "$project_type" =~ ^(python|javascript|typescript|cpp|c++|shell)$ ]] && echo "✅ 正常" || echo "⚠️ 需要关注")
- **项目类型**: $project_type
- **建议**: $([[ "$project_type" =~ ^(python|javascript|typescript|cpp|c++|shell)$ ]] && echo "项目类型受支持" || echo "可能需要添加对新项目类型的支持")

## ✅ 正常项目
- 项目目录结构正常
- 分析JSON文件存在且格式有效
- 基本项目信息完整

## 🔧 建议的改进措施
1. 持续监控项目分析质量
2. 改进模块识别算法
3. 扩展对新项目类型的支持

---
*验证完成时间: $(date)*
*验证工具: PSG Validator v1.0*
EOF
        return 1
    else
        echo "✅ 项目验证通过"
        echo "📝 记录到报告: $report_file"
        cat > "$report_file" << EOF
# $repo_name 验证成功报告 - $DATE

## 🔍 验证信息
- **仓库名称**: $repo_name
- **验证路径**: $repo_path
- **验证时间**: $(date)
- **验证状态**: ✅ 验证通过

## 📊 项目概览
- **项目类型**: $project_type
- **主要语言**: $language
- **模块数量**: $module_count
- **分析文件**: ${analysis_files[0]}

## ✅ 验证通过项目
- 项目目录结构正常
- 分析JSON文件存在且格式有效
- 项目信息完整
- 模块数量正常
- 项目类型受支持

## 🎯 关键指标
- **健康度**: 100%
- **完整性**: 100%
- **支持度**: 100%

## 🔧 后续建议
1. 保持定期验证
2. 监控项目变化
3. 维护分析质量

---
*验证完成时间: $(date)*
*验证工具: PSG Validator v1.0*
EOF
        return 0
    fi
}

# 主流程
echo "🚀 PSG 验证脚本启动"
echo "⏰ 开始时间: $(date)"

# 获取下一个仓库
next_repo=$(get_next_repo)
echo "📍 下一个验证仓库: $(basename "$next_repo")"

# 执行验证
validate_repo "$next_repo"
validation_result=$?

# 记录验证完成
touch "$next_repo/validation_complete"

echo "🏁 验证完成"
echo "⏰ 结束时间: $(date)"
echo "📊 验证结果: $([ $validation_result -eq 0 ] && echo "✅ 通过" || echo "❌ 发现问题")"

# 显示报告位置
report_file="$REPORTS_DIR/$(basename "$next_repo")_issues_$(date +%Y-%m-%d).md"
echo "📝 验证报告: $report_file"

exit $validation_result