#!/bin/bash
#
# Remote Shell 快速启动脚本
#

cd "$(dirname "$0")/.."
INSTALL_DIR="$(pwd)"
CONFIG_DIR="/etc/remote-shell"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 显示 Banner
show_banner() {
    echo -e "${GREEN}"
    echo "  ╔═════════════════════════════════════════╗"
    echo "  ║     🔺 Remote Shell 远程管理工具        ║"
    echo "  ║         快速启动脚本 v1.0               ║"
    echo "  ╚═════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查依赖
check_deps() {
    echo -e "${YELLOW}[*] 检查依赖...${NC}"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}[✗] 未安装 Python3${NC}"
        exit 1
    fi
    
    # 检查 aiohttp
    if ! python3 -c "import aiohttp" 2>/dev/null; then
        echo -e "${YELLOW}[*] 安装 aiohttp...${NC}"
        pip3 install aiohttp -q
    fi
    
    echo -e "${GREEN}[✓] 依赖检查通过${NC}"
}

# 初始化配置
init_config() {
    if [ ! -f "$CONFIG_DIR/config.json" ]; then
        echo -e "${YELLOW}[*] 初始化配置...${NC}"
        mkdir -p "$CONFIG_DIR"
        
        # 生成 Token
        TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(16))")
        WEB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(8))")
        
        # 检测公网 IP
        PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
        
        cat > "$CONFIG_DIR/config.json" << EOF
{
    "server": {
        "host": "0.0.0.0",
        "port": 9527,
        "token": "$TOKEN"
    },
    "web": {
        "enabled": true,
        "host": "0.0.0.0",
        "port": 9528,
        "username": "admin",
        "password": "$WEB_PASSWORD"
    },
    "tls": {
        "enabled": false,
        "cert_file": "$CONFIG_DIR/server.crt",
        "key_file": "$CONFIG_DIR/server.key"
    },
    "log": {
        "level": "INFO",
        "file": "/var/log/remote-shell/remote-shell.log"
    },
    "public_ip": "$PUBLIC_IP"
}
EOF
        
        echo -e "${GREEN}[✓] 配置已创建${NC}"
    fi
}

# 显示配置
show_config() {
    if [ -f "$CONFIG_DIR/config.json" ]; then
        TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_DIR/config.json'))['server']['token'])")
        WEB_PASSWORD=$(python3 -c "import json; print(json.load(open('$CONFIG_DIR/config.json'))['web']['password'])")
        PUBLIC_IP=$(python3 -c "import json; print(json.load(open('$CONFIG_DIR/config.json')).get('public_ip', 'N/A'))")
        
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════${NC}"
        echo -e "  连接信息"
        echo -e "${GREEN}═══════════════════════════════════════════${NC}"
        echo ""
        echo -e "  服务器地址: ${YELLOW}$PUBLIC_IP:9527${NC}"
        echo -e "  连接 Token: ${YELLOW}$TOKEN${NC}"
        echo ""
        echo -e "  Web 管理界面: ${YELLOW}http://$PUBLIC_IP:9528${NC}"
        echo -e "  用户名: ${YELLOW}admin${NC}"
        echo -e "  密码: ${YELLOW}$WEB_PASSWORD${NC}"
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════${NC}"
        echo ""
    fi
}

# 启动服务
start_server() {
    show_banner
    check_deps
    init_config
    show_config
    
    echo -e "${YELLOW}[*] 启动服务端...${NC}"
    echo ""
    
    # 后台启动
    python3 "$INSTALL_DIR/server/server.py" --config "$CONFIG_DIR/config.json" &
    SERVER_PID=$!
    echo $SERVER_PID > /tmp/remote-shell-server.pid
    
    sleep 1
    
    if kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${GREEN}[✓] 服务端已启动 (PID: $SERVER_PID)${NC}"
    else
        echo -e "${RED}[✗] 服务端启动失败${NC}"
        exit 1
    fi
    
    # 询问是否启动 Web
    echo ""
    read -p "是否启动 Web 管理界面？(Y/n): " choice
    case "$choice" in
        n|N )
            echo -e "${YELLOW}[*] 跳过 Web 界面${NC}"
            ;;
        * )
            echo -e "${YELLOW}[*] 启动 Web 管理界面...${NC}"
            python3 "$INSTALL_DIR/web/web_server.py" --config "$CONFIG_DIR/config.json" &
            WEB_PID=$!
            echo $WEB_PID > /tmp/remote-shell-web.pid
            
            sleep 1
            
            if kill -0 $WEB_PID 2>/dev/null; then
                echo -e "${GREEN}[✓] Web 界面已启动 (PID: $WEB_PID)${NC}"
            else
                echo -e "${RED}[✗] Web 界面启动失败${NC}"
            fi
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "  ${GREEN}全部启动完成！${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""
    echo "  停止服务: $0 --stop"
    echo "  查看状态: $0 --status"
    echo ""
}

# 停止服务
stop_server() {
    echo -e "${YELLOW}[*] 停止服务...${NC}"
    
    if [ -f /tmp/remote-shell-server.pid ]; then
        kill $(cat /tmp/remote-shell-server.pid) 2>/dev/null
        rm /tmp/remote-shell-server.pid
        echo -e "${GREEN}[✓] 服务端已停止${NC}"
    fi
    
    if [ -f /tmp/remote-shell-web.pid ]; then
        kill $(cat /tmp/remote-shell-web.pid) 2>/dev/null
        rm /tmp/remote-shell-web.pid
        echo -e "${GREEN}[✓] Web 界面已停止${NC}"
    fi
}

# 查看状态
show_status() {
    echo ""
    echo "服务状态:"
    echo ""
    
    if [ -f /tmp/remote-shell-server.pid ] && kill -0 $(cat /tmp/remote-shell-server.pid) 2>/dev/null; then
        echo -e "  服务端: ${GREEN}● 运行中${NC} (PID: $(cat /tmp/remote-shell-server.pid))"
    else
        echo -e "  服务端: ${RED}○ 未运行${NC}"
    fi
    
    if [ -f /tmp/remote-shell-web.pid ] && kill -0 $(cat /tmp/remote-shell-web.pid) 2>/dev/null; then
        echo -e "  Web 界面: ${GREEN}● 运行中${NC} (PID: $(cat /tmp/remote-shell-web.pid))"
    else
        echo -e "  Web 界面: ${RED}○ 未运行${NC}"
    fi
    
    echo ""
}

# 主流程
case "$1" in
    --stop)
        stop_server
        ;;
    --status)
        show_status
        ;;
    --config)
        show_config
        ;;
    *)
        start_server
        ;;
esac
