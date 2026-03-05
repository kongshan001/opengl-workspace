#!/bin/bash
# PreToolUse Hook: 安全检查
# 在执行 Bash 命令前进行安全验证

set -e

# 读取 JSON 输入
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 如果没有命令，直接允许
if [ -z "$COMMAND" ]; then
  exit 0
fi

# ============================================
# 危险命令黑名单
# ============================================
DANGEROUS_PATTERNS=(
    # 文件系统破坏
    "^rm -rf /$"
    "^rm -rf /*$"
    "^rm -rf ~"
    "^rm -rf \$HOME"
    "^rm -rf \.\."
    
    # Fork 炸弹
    "^:\\(\\) \\{ :\\|:& \\};:"
    
    # 磁盘操作
    "^mkfs\."
    "^dd if=.*of=/dev/"
    "^> /dev/sd"
    "^> /dev/hd"
    
    # 权限变更
    "^chmod -R 777 /$"
    "^chmod -R 777 ~$"
    "^chown -R .* /$"
    
    # 远程执行
    "curl.*|.*bash"
    "wget.*|.*bash"
    "curl.*|.*sh"
    "wget.*|.*sh"
    
    # 环境破坏
    "^export PATH=.*:$"  # 清空 PATH
)

# 检查危险模式
for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        jq -n "{
            hookSpecificOutput: {
                hookEventName: \"PreToolUse\",
                permissionDecision: \"deny\",
                permissionDecisionReason: \"🚫 禁止执行危险命令: 检测到危险模式 '$pattern'\"
            }
        }"
        exit 0
    fi
done

# ============================================
# 敏感文件保护
# ============================================
SENSITIVE_PATTERNS=(
    "\.env$"
    "\.env\."
    "\.pem$"
    "\.key$"
    "credentials"
    "secrets?/"
    "id_rsa"
    "\.npmrc$"
    "\.netrc$"
)

# 检查是否操作敏感文件
for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        jq -n "{
            hookSpecificOutput: {
                hookEventName: \"PreToolUse\",
                permissionDecision: \"ask\",
                permissionDecisionReason: \"⚠️ 该命令可能涉及敏感文件，请确认是否继续执行\"
            }
        }"
        exit 0
    fi
done

# ============================================
# 生产环境保护
# ============================================
if echo "$COMMAND" | grep -qE "(prod|production)" && echo "$COMMAND" | grep -qE "(drop|delete|truncate|rm)"; then
    jq -n "{
        hookSpecificOutput: {
            hookEventName: \"PreToolUse\",
            permissionDecision: \"ask\",
            permissionDecisionReason: \"⚠️ 该命令可能影响生产环境，请确认是否继续执行\"
        }
    }"
    exit 0
fi

# ============================================
# 允许执行
# ============================================
exit 0
