"""
X (Twitter) 账户监控器 - 主入口
"""

import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from x_twitter_monitor.app import XMonitorApp

    app = XMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
