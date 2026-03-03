# TOOLS.md - 本地工具配置

## 开发环境

- **系统**: Linux (Ubuntu 24.04)
- **编译器**: GCC 13.3.0
- **构建工具**: CMake 3.28
- **OpenGL**: 3.3 Core Profile

## 图形相关

- **GLFW**: 窗口管理 (系统安装: /usr/lib/x86_64-linux-gnu)
- **GLAD**: OpenGL 加载器
- **虚拟显示**: Xvfb :99 (无物理显示器)

## 编译命令

```bash
cd /path/to/project
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

## 运行命令

```bash
# 使用虚拟显示
DISPLAY=:99 ./your_program

# 截图验证
DISPLAY=:99 import -window root /tmp/screenshot.png
```

## 代码风格

- 命名：类名 PascalCase，函数/变量 camelCase，常量 UPPER_CASE
- 缩进：4 空格
- 花括号：K&R 风格
