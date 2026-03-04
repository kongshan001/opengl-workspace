#!/bin/bash
# GitHub Project Analyzer - 数据采集模块
# 用法: ./collector.sh <github_url> [output_dir]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 解析参数
GITHUB_URL="$1"
OUTPUT_DIR="${2:-./output}"

if [ -z "$GITHUB_URL" ]; then
    echo -e "${RED}错误: 请提供 GitHub URL${NC}"
    echo "用法: $0 <github_url> [output_dir]"
    exit 1
fi

# 解析 GitHub URL
# 支持格式:
# - https://github.com/owner/repo
# - https://github.com/owner/repo.git
# - git@github.com:owner/repo.git

parse_github_url() {
    local url="$1"
    local owner repo

    # 移除 .git 后缀
    url="${url%.git}"

    # 提取 owner 和 repo
    if [[ "$url" =~ github\.com/([^/]+)/([^/]+) ]]; then
        owner="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]}"
    else
        echo -e "${RED}错误: 无法解析 GitHub URL${NC}"
        exit 1
    fi

    echo "$owner $repo"
}

read OWNER REPO <<< $(parse_github_url "$GITHUB_URL")

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  GitHub Project Analyzer - 数据采集${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "  仓库: ${GREEN}$OWNER/$REPO${NC}"
echo -e "  输出: ${GREEN}$OUTPUT_DIR${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# 创建输出目录
mkdir -p "$OUTPUT_DIR/data"
mkdir -p "$OUTPUT_DIR/analysis"
mkdir -p "$OUTPUT_DIR/docs"
mkdir -p "$OUTPUT_DIR/images"
mkdir -p "$OUTPUT_DIR/video"

# 检查 gh 是否已认证
if ! gh auth status &>/dev/null; then
    echo -e "${RED}错误: gh 未认证，请先运行 'gh auth login'${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[1/6] 采集仓库元数据...${NC}"

# 获取仓库基本信息
gh repo view "$OWNER/$REPO" --json name,description,url,homepageUrl,stargazerCount,forkCount,watchers,languages,licenseInfo,createdAt,updatedAt,pushedAt,isArchived,isFork,isTemplate,visibility,owner,defaultBranchRef,repositoryTopics,primaryLanguage > "$OUTPUT_DIR/data/repo_metadata.json"

echo -e "  ${GREEN}✓${NC} 仓库元数据已保存"

echo ""
echo -e "${YELLOW}[2/6] 采集贡献者信息...${NC}"

# 获取贡献者 (通过 API)
gh api "repos/$OWNER/$REPO/contributors" \
    --paginate \
    --jq '.[].login' \
    2>/dev/null | head -50 > "$OUTPUT_DIR/data/contributors.txt" || echo "无法获取贡献者列表"

CONTRIBUTOR_COUNT=$(wc -l < "$OUTPUT_DIR/data/contributors.txt" 2>/dev/null || echo "0")
echo -e "  ${GREEN}✓${NC} 贡献者列表 ($CONTRIBUTOR_COUNT 人)"

echo ""
echo -e "${YELLOW}[3/6] 采集 README 内容...${NC}"

# 获取 README
gh api "repos/$OWNER/$REPO/readme" \
    --jq '.content' \
    2>/dev/null | base64 -d > "$OUTPUT_DIR/data/readme.md" 2>/dev/null || echo "# README 未找到" > "$OUTPUT_DIR/data/readme.md"

echo -e "  ${GREEN}✓${NC} README 已保存"

echo ""
echo -e "${YELLOW}[4/6] 采集代码结构...${NC}"

# 获取代码树结构
gh api "repos/$OWNER/$REPO/git/trees/main?recursive=1" \
    --jq '.tree[].path' \
    2>/dev/null > "$OUTPUT_DIR/data/file_tree.txt" || \
gh api "repos/$OWNER/$REPO/git/trees/master?recursive=1" \
    --jq '.tree[].path' \
    2>/dev/null > "$OUTPUT_DIR/data/file_tree.txt" || \
echo "无法获取文件树"

# 分析语言分布
if [ -f "$OUTPUT_DIR/data/repo_metadata.json" ]; then
    cat "$OUTPUT_DIR/data/repo_metadata.json" | jq -r '.languages.edges[] | "\(.node.name): \(.size)"' 2>/dev/null > "$OUTPUT_DIR/data/languages.txt" || true
fi

FILE_COUNT=$(wc -l < "$OUTPUT_DIR/data/file_tree.txt" 2>/dev/null || echo "0")
echo -e "  ${GREEN}✓${NC} 文件树 ($FILE_COUNT 个文件)"

echo ""
echo -e "${YELLOW}[5/6] 采集发布历史...${NC}"

# 获取最近的 releases
gh release list --repo "$OWNER/$REPO" --limit 20 \
    --json tagName,name,publishedAt,description \
    > "$OUTPUT_DIR/data/releases.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/data/releases.json"

RELEASE_COUNT=$(jq length "$OUTPUT_DIR/data/releases.json" 2>/dev/null || echo "0")
echo -e "  ${GREEN}✓${NC} 发布历史 ($RELEASE_COUNT 个版本)"

echo ""
echo -e "${YELLOW}[6/6] 采集 Issues 摘要...${NC}"

# 获取最近的 issues
gh issue list --repo "$OWNER/$REPO" --limit 50 --state all \
    --json number,title,state,createdAt,labels,comments \
    > "$OUTPUT_DIR/data/issues.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/data/issues.json"

ISSUE_COUNT=$(jq length "$OUTPUT_DIR/data/issues.json" 2>/dev/null || echo "0")
echo -e "  ${GREEN}✓${NC} Issues 摘要 ($ISSUE_COUNT 条)"

# 生成采集摘要
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  数据采集完成！${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# 输出摘要信息
STARS=$(jq -r '.stargazerCount' "$OUTPUT_DIR/data/repo_metadata.json")
FORKS=$(jq -r '.forkCount' "$OUTPUT_DIR/data/repo_metadata.json")
LANG=$(jq -r '.primaryLanguage.name' "$OUTPUT_DIR/data/repo_metadata.json")
DESC=$(jq -r '.description' "$OUTPUT_DIR/data/repo_metadata.json")

cat << EOF

📊 仓库概览
   名称: $OWNER/$REPO
   描述: $DESC
   语言: $LANG
   Stars: $STARS ⭐
   Forks: $FORKS 🍴

📁 输出文件
   $OUTPUT_DIR/data/
   ├── repo_metadata.json    # 仓库元数据
   ├── readme.md             # README 内容
   ├── file_tree.txt         # 文件树
   ├── languages.txt         # 语言分布
   ├── contributors.txt      # 贡献者列表
   ├── releases.json         # 发布历史
   └── issues.json           # Issues 摘要

EOF

# 保存仓库标识供后续使用
echo "$OWNER/$REPO" > "$OUTPUT_DIR/.repo_info"
