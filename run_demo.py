#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AQ-用户标签系统启动脚本
"""

import os
import sys
from web.app import app

def ensure_directories():
    """确保必要的目录存在"""
    dirs_to_create = [
        'user_data',
        'web/static',
        'web/templates'
    ]
    
    for dir_path in dirs_to_create:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✓ 确保目录存在: {dir_path}")

def main():
    """主函数"""
    print("🚀 启动 AQ-用户标签系统...")
    
    # 确保目录存在
    ensure_directories()
    
    # 检查配置文件
    if not os.path.exists('config.yaml'):
        print("❌ 错误: config.yaml 配置文件不存在")
        sys.exit(1)
    
    print("✓ 配置文件检查完成")
    print("🌐 启动Web服务器...")
    print("📱 请在浏览器中访问: http://127.0.0.1:8080")
    
    # 启动Flask应用
    app.run(
        host='127.0.0.1',
        port=8080,
        debug=True
    )

if __name__ == '__main__':
    main()
