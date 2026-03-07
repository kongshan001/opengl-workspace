#!/bin/bash
#
# Remote Shell 快速连接脚本
#

cd "$(dirname "$0")/.."
INSTALL_DIR="$(pwd)"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_usage() {
    echo -e "${GREEN}"
    echo "  Remote Shell 客户端"
    echo -e "${NC}"
    echo "用法:"
    echo "  $0 <服务器地址> <Token> [命令]"
    echo ""
    echo "示例:"
    echo "  # 交互模式"
    echo "  $0 192.168.1.100 abc123def456..."
    echo ""
    echo "  # 单次命令"
    echo "  $0 192.168.1.100 abc123def456... 'ls -la'"
    echo ""
    echo "  # 从配置文件读取"
    echo "  $0 --from-config /etc/remote-shell/config.json"
}

# 从参数连接
connect_args() {
    local HOST=$1
    local TOKEN=$2
    local CMD=$3
    
    if [ -z "$HOST" ] || [ -z "$TOKEN" ]; then
        show_usage
        exit 1
    fi
    
    echo -e "${GREEN}[+] 连接到 $HOST...${NC}"
    
    if [ -n "$CMD" ]; then
        python3 "$INSTALL_DIR/client/client.py" --host "$HOST" --token "$TOKEN" -c "$CMD"
    else
        python3 "$INSTALL_DIR/client/client.py" --host "$HOST" --token "$TOKEN"
    fi
}

# 从配置文件连接
connect_config() {
    local CONFIG=$1
    
    if [ ! -f "$CONFIG" ]; then
        echo -e "${RED}[!] 配置文件不存在: $CONFIG${NC}"
        exit 1
    fi
    
    HOST=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c.get('public_ip', '127.0.0.1'))")
    TOKEN=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['server']['token'])")
    
    echo -e "${GREEN}[+] 从配置文件加载连接信息${NC}"
    echo -e "    服务器: $HOST"
    echo ""
    
    python3 "$INSTALL_DIR/client/client.py" --host "$HOST" --token "$TOKEN"
}

# 主流程
case "$1" in
    -h|--help)
        show_usage
        ;;
    --from-config)
        connect_config "$2"
        ;;
    *)
        connect_args "$1" "$2" "$3"
        ;;
esac
