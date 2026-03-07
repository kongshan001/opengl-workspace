#!/bin/bash
#
# Remote Shell 一键安装脚本
# 使用: curl -fsSL https://your-server/install.sh | bash
#

set -e

INSTALL_DIR="/opt/remote-shell"
CONFIG_DIR="/etc/remote-shell"
LOG_DIR="/var/log/remote-shell"

echo "================================================"
echo "    Remote Shell 远程管理工具 - 安装向导"
echo "================================================"
echo ""

# 检查 Python 版本
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo "[✓] 检测到 Python $PYTHON_VERSION"
    else
        echo "[✗] 未检测到 Python3，请先安装 Python 3.8+"
        exit 1
    fi
}

# 创建目录
create_dirs() {
    echo "[*] 创建目录..."
    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p "$CONFIG_DIR"
    sudo mkdir -p "$LOG_DIR"
    sudo chown -R $USER:$USER "$INSTALL_DIR" 2>/dev/null || true
    sudo chown -R $USER:$USER "$CONFIG_DIR" 2>/dev/null || true
    sudo chown -R $USER:$USER "$LOG_DIR" 2>/dev/null || true
}

# 复制文件
copy_files() {
    echo "[*] 复制程序文件..."
    
    # 获取脚本所在目录（如果是本地安装）
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # 复制所有文件
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || {
        echo "[!] 本地文件不存在，创建基础文件..."
        # 如果没有本地文件，创建基础结构
        mkdir -p "$INSTALL_DIR"/{common,server,client,web,scripts,config}
    }
    
    # 设置执行权限
    chmod +x "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true
    chmod +x "$INSTALL_DIR/server/server.py" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/client/client.py" 2>/dev/null || true
}

# 生成配置
generate_config() {
    echo "[*] 生成配置文件..."
    
    CONFIG_FILE="$CONFIG_DIR/config.json"
    
    if [ -f "$CONFIG_FILE" ]; then
        echo "[!] 配置文件已存在，跳过"
        echo "    如需重新配置，请运行: remote-shell config"
        return
    fi
    
    # 自动生成 Token
    TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || openssl rand -hex 16 2>/dev/null || echo "change_this_token")
    
    # 检测公网 IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "YOUR_SERVER_IP")
    
    # 生成配置
    cat > "$CONFIG_FILE" << EOF
{
    "server": {
        "host": "0.0.0.0",
        "port": 9527,
        "token": "$TOKEN"
    },
    "web": {
        "enabled": true,
        "host": "0.0.0.0",
        "port": 9528
    },
    "tls": {
        "enabled": false,
        "cert_file": "$CONFIG_DIR/server.crt",
        "key_file": "$CONFIG_DIR/server.key"
    },
    "log": {
        "level": "INFO",
        "file": "$LOG_DIR/remote-shell.log"
    },
    "public_ip": "$PUBLIC_IP"
}
EOF
    
    echo "[✓] 配置文件已创建: $CONFIG_FILE"
    echo ""
    echo "    服务器地址: $PUBLIC_IP:9527"
    echo "    Web 管理界面: http://$PUBLIC_IP:9528"
    echo "    认证 Token: $TOKEN"
    echo ""
    echo "    ⚠️  请保存好 Token，这是连接服务器的密码！"
}

# 生成 TLS 证书（自签名）
generate_tls_cert() {
    echo ""
    read -p "[?] 是否生成自签名 TLS 证书？(y/N): " choice
    case "$choice" in
        y|Y )
            echo "[*] 生成自签名证书..."
            openssl req -x509 -newkey rsa:2048 -keyout "$CONFIG_DIR/server.key" \
                -out "$CONFIG_DIR/server.crt" -days 365 -nodes \
                -subj "/CN=RemoteShell" 2>/dev/null
            
            # 更新配置启用 TLS
            python3 -c "
import json
with open('$CONFIG_DIR/config.json', 'r') as f:
    config = json.load(f)
config['tls']['enabled'] = True
with open('$CONFIG_DIR/config.json', 'w') as f:
    json.dump(config, f, indent=4)
" 2>/dev/null || true
            
            echo "[✓] TLS 证书已生成"
            ;;
        * )
            echo "[*] 跳过 TLS 证书生成"
            ;;
    esac
}

# 创建便捷命令
create_command() {
    echo "[*] 创建快捷命令..."
    
    cat > /usr/local/bin/remote-shell << 'CMD_EOF'
#!/bin/bash
# Remote Shell 快捷命令

INSTALL_DIR="/opt/remote-shell"
CONFIG_DIR="/etc/remote-shell"

case "$1" in
    start)
        cd "$INSTALL_DIR"
        python3 server/server.py --config "$CONFIG_DIR/config.json" &
        echo $! > /tmp/remote-shell.pid
        echo "[✓] 服务已启动 (PID: $(cat /tmp/remote-shell.pid))"
        ;;
    stop)
        if [ -f /tmp/remote-shell.pid ]; then
            kill $(cat /tmp/remote-shell.pid) 2>/dev/null
            rm /tmp/remote-shell.pid
            echo "[✓] 服务已停止"
        else
            echo "[!] 服务未运行"
        fi
        ;;
    status)
        if [ -f /tmp/remote-shell.pid ] && kill -0 $(cat /tmp/remote-shell.pid) 2>/dev/null; then
            echo "[✓] 服务运行中 (PID: $(cat /tmp/remote-shell.pid))"
        else
            echo "[✗] 服务未运行"
        fi
        ;;
    connect)
        shift
        python3 "$INSTALL_DIR/client/client.py" "$@"
        ;;
    config)
        ${EDITOR:-nano} "$CONFIG_DIR/config.json"
        ;;
    show-config)
        cat "$CONFIG_DIR/config.json"
        ;;
    logs)
        tail -f "$CONFIG_DIR/../log/remote-shell/remote-shell.log" 2>/dev/null || \
            tail -f "/var/log/remote-shell/remote-shell.log"
        ;;
    web)
        echo "启动 Web 管理界面..."
        cd "$INSTALL_DIR"
        python3 web/web_server.py --config "$CONFIG_DIR/config.json" &
        ;;
    *)
        echo "Remote Shell 远程管理工具"
        echo ""
        echo "用法: remote-shell <命令> [参数]"
        echo ""
        echo "命令:"
        echo "  start        启动服务端"
        echo "  stop         停止服务端"
        echo "  status       查看状态"
        echo "  connect      连接到服务器 (需 --host 和 --token)"
        echo "  config       编辑配置文件"
        echo "  show-config  显示配置信息"
        echo "  logs         查看日志"
        echo "  web          启动 Web 管理界面"
        echo ""
        echo "示例:"
        echo "  remote-shell start"
        echo "  remote-shell connect --host 192.168.1.100 --token YOUR_TOKEN"
        echo "  remote-shell connect --host 192.168.1.100 --token YOUR_TOKEN -c 'ls -la'"
        ;;
esac
CMD_EOF
    
    chmod +x /usr/local/bin/remote-shell 2>/dev/null || {
        echo "[!] 需要 sudo 权限创建全局命令"
        echo "    请运行: sudo chmod +x /usr/local/bin/remote-shell"
    }
    
    echo "[✓] 快捷命令已创建: remote-shell"
}

# 显示使用说明
show_usage() {
    echo ""
    echo "================================================"
    echo "           安装完成！"
    echo "================================================"
    echo ""
    echo "🚀 快速开始:"
    echo ""
    echo "  1. 启动服务端:"
    echo "     remote-shell start"
    echo ""
    echo "  2. 连接到服务器:"
    echo "     remote-shell connect --host <服务器IP> --token <TOKEN>"
    echo ""
    echo "  3. 查看配置:"
    echo "     remote-shell show-config"
    echo ""
    echo "  4. 启动 Web 管理界面:"
    echo "     remote-shell web"
    echo ""
    echo "📁 文件位置:"
    echo "  程序目录: $INSTALL_DIR"
    echo "  配置文件: $CONFIG_DIR/config.json"
    echo "  日志目录: $LOG_DIR"
    echo ""
}

# 主流程
main() {
    check_python
    create_dirs
    copy_files
    generate_config
    generate_tls_cert
    create_command
    show_usage
}

main
