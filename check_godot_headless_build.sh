#!/bin/bash

# Godot Headless 编译监控脚本
BUILD_LOG="/tmp/godot_headless_build.log"
BUILD_DIR="/root/.openclaw/workspace-opengl/godot-validation"
NOTIFICATION_FILE="/tmp/godot_headless_build_notified"

# 检查编译进程是否还在运行
if ! ps aux | grep -q "[s]cons.*headless"; then
    # 编译进程已结束
    
    # 检查是否已经发送过通知
    if [ -f "$NOTIFICATION_FILE" ]; then
        exit 0
    fi
    
    # 检查是否编译成功 - headless 版本的可执行文件名
    if [ -f "$BUILD_DIR/bin/godot.linuxbsd.template_release.x86_64" ]; then
        # 编译成功
        MESSAGE="✅ Godot Headless 编译成功！\n\n可执行文件位置：\n$BUILD_DIR/bin/godot.linuxbsd.template_release.x86_64\n\n特性：无窗口化运行，适合服务器环境\n编译日志：$BUILD_LOG"
        
        # 记录编译成功信息到文件
        echo "SUCCESS: $(date)" > "$NOTIFICATION_FILE"
        
        # 发送飞书通知
        /usr/bin/openclaw message send --channel feishu --target user:ou_15ff1d12b1e893ad7ae94f8124798591 --message "$MESSAGE" 2>&1 || true
        
        exit 0
    else
        # 编译失败
        MESSAGE="❌ Godot Headless 编译失败\n\n请检查编译日志：$BUILD_LOG"
        
        # 记录编译失败信息到文件
        echo "FAILED: $(date)" > "$NOTIFICATION_FILE"
        
        # 发送飞书通知
        /usr/bin/openclaw message send --channel feishu --target user:ou_15ff1d12b1e893ad7ae94f8124798591 --message "$MESSAGE" 2>&1 || true
        
        exit 1
    fi
fi

# 编译仍在进行中
exit 0
