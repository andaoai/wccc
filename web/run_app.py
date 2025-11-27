#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit应用启动脚本
"""

import subprocess
import sys
import os

def main():
    """启动Streamlit应用"""
    # 获取当前脚本目录的父目录（项目根目录）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_path = os.path.join(project_root, "web", "data_visualization.py")

    print(f"🚀 启动微信消息数据分析平台...")
    print(f"📁 应用路径: {app_path}")
    print(f"🌐 应用将在浏览器中打开: http://localhost:8501")
    print("=" * 50)

    try:
        # 启动Streamlit应用
        cmd = [
            sys.executable, "-m", "streamlit", "run", app_path,
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ]

        subprocess.run(cmd, cwd=project_root)

    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()