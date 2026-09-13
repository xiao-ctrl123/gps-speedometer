"""车速仪表盘 —— 应用入口。

桌面调试：  python main.py
Android 打包：buildozer android debug deploy run
"""

from speedometer.app import SpeedometerApp


if __name__ == '__main__':
    SpeedometerApp().run()
