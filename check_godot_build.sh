#!/bin/bash

# Godot 编译监控脚本
BUILD_LOG="/tmp/godot_build.log"
BUILD_DIR="/root/.openclaw/workspace-opengl/godot-validation"
NOTIFICATION_FILE="/tmp/godot_build_notified"

# 检查编译进程是否还在运行
if ! ps aux | grep -q "[s]cons.*godot"; then
    # 编译进程已结束
    
    # 检查是否已经发送过通知
    if [ -f "$NOTIFICATION_FILE" ]; then
        exit 0
    fi
    
    # 检查是否编译成功
    if [ -f "$BUILD_DIR/bin/godot.linuxbsd.template_release.x86_64" ]; then
        # 编译成功
        MESSAGE="✅ Godot 编译成功！\n\n可执行文件位置：\n$BUILD_DIR/bin/godot.linuxbsd.template_release.x86_64\n\n编译日志：$BUILD_LOG"
        
        # 记录编译成功信息到文件
        echo "SUCCESS: $(date)" > "$NOTIFICATION_FILE"
        
        # 发送飞书通知
        /usr/bin/openclaw message send --channel feishu --message "$MESSAGE" 2>&1 || true
        
        exit 0
    else
        # 编译失败
        MESSAGE="❌ Godot 编译失败\n\n请检查编译日志：$BUILD_LOG"
        
        # 记录编译失败信息到文件
        echo "FAILED: $(date)" > "$NOTIFICATION_FILE"
        
        # 发送飞书通知
        /usr/bin/openclaw message send --channel feishu --message "$MESSAGE" 2>&1 || true
        
        exit 1
    fi
fi

# 编译仍在进行中
exit 0
