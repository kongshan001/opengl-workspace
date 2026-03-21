# 🔺 Remote Shell v2.0 - 远程管理工具

一个**傻瓜式**的全功能远程计算机管理工具。

![Version](https://img.shields.io/badge/version-2.1.0-green)
![Python](https://img.shields.io/badge/python-3.8+-blue)

---

## ✨ 功能一览

| 模块 | 功能 | 状态 |
|------|------|------|
| **终端** | 远程执行命令、交互式 Shell | ✅ |
| **文件** | 浏览目录、上传/下载文件 | ✅ |
| **监控** | CPU/内存/磁盘/进程监控 | ✅ |
| **隧道** | TCP 端口转发 | ✅ |
| **用户** | 多用户管理、权限控制 | ✅ |
| **安全** | Token 认证、TLS 加密 | ✅ |
| **审计** | 操作日志、登录日志、日志查询 | ✅ |

---

## 🚀 5 秒快速开始

### 服务端（被控机器）

```bash
cd remote-shell
./scripts/start.sh
```

输出：
```
═══════════════════════════════════════════
  连接信息
═══════════════════════════════════════════

  服务器地址: 192.168.1.100:9527
  连接 Token: abc123def456...

  Web 管理界面: http://192.168.1.100:9528
  用户名: admin
  密码: xyz789...
```

### 客户端（控制端）

**方式一：浏览器**（最简单）

```
http://192.168.1.100:9528
```

**方式二：命令行**

```bash
# 交互模式
python3 client/client.py --host 192.168.1.100 --token YOUR_TOKEN

# 单次命令
python3 client/client.py --host 192.168.1.100 --token YOUR_TOKEN -c "ls -la"
```

---

## 🖥️ Web 界面功能

### 1. 终端标签
- 执行任意 Shell 命令
- 彩色输出（stdout/stderr）
- 命令历史

### 2. 文件标签
- 浏览远程目录
- 点击下载文件
- 拖拽上传文件
- 显示文件大小

### 3. 监控标签
- 实时 CPU/内存/磁盘使用率
- 进度条可视化
- 系统运行时间
- 负载信息

### 4. 隧道标签
- 创建 TCP 端口转发
- 查看连接统计
- 一键删除隧道

### 5. 用户标签
- 创建/删除用户
- 权限管理
- 密码修改

---

## 📋 权限系统

| 权限 | 说明 |
|------|------|
| `exec` | 执行命令 |
| `file_read` | 读取文件 |
| `file_write` | 写入文件 |
| `admin` | 管理员（全部权限） |

---

## 🔧 配置文件

位置：`/etc/remote-shell/config.json`

```json
{
    "server": {
        "host": "0.0.0.0",
        "port": 9527,
        "token": "your_token"
    },
    "web": {
        "host": "0.0.0.0",
        "port": 9528,
        "username": "admin",
        "password": "your_password"
    },
    "tls": {
        "enabled": false
    }
}
```

---

## 📁 项目结构

```
remote-shell/
├── scripts/
│   ├── start.sh          # 一键启动
│   └── connect.sh        # 快速连接
├── server/
│   └── server.py         # 服务端
├── client/
│   └── client.py         # 命令行客户端
├── web/
│   └── web_server.py     # Web 管理界面
├── common/
│   ├── protocol.py       # 通信协议
│   ├── config.py         # 配置管理
│   ├── users.py          # 用户管理
│   ├── monitor.py        # 系统监控
│   └── tunnel.py         # 端口转发
├── install.sh            # 一键安装
└── README.md
```

---

## 🔒 安全建议

1. **强密码**：使用至少 16 位随机 Token
2. **TLS 加密**：生产环境启用 TLS
3. **防火墙**：限制访问来源 IP
4. **最小权限**：普通用户只给必要权限
5. **日志审计**：定期检查 `/var/log/remote-shell/`

---

## 📝 更新日志

### v2.0.0
- ✅ 多用户管理
- ✅ 权限系统
- ✅ 系统监控
- ✅ 端口转发
- ✅ Web 界面重构

### v1.0.0
- ✅ 远程命令执行
- ✅ 文件传输
- ✅ Token 认证

---

## 📄 License

MIT License
