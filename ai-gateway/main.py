#!/usr/bin/env python3
"""
AI Gateway - AI API 代理网关

快速启动:
    python main.py serve

用户管理:
    python main.py user create <name>
    python main.py user list
"""
import sys
from pathlib import Path

# 确保可以导入模块
sys.path.insert(0, str(Path(__file__).parent))

from cli.main import cli

if __name__ == "__main__":
    cli()
