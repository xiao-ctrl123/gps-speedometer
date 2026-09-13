"""开发辅助脚本：把半圆车速表渲染成 PNG 方便预览配色与布局。

用法：
    python preview.py [速度值]
生成 preview.png。
"""

import os
import sys

os.environ.setdefault('KIVY_NO_ARGS', '1')

from kivy.config import Config  # noqa: E402

Config.set('graphics', 'width', '480')
Config.set('graphics', 'height', '480')
Config.set('graphics', 'resizable', '0')

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402

from speedometer.fonts import register_cjk_font  # noqa: E402
from speedometer.speed_arc import SpeedArc  # noqa: E402


class PreviewApp(App):
    def build(self):
        register_cjk_font()
        speed = float(sys.argv[1]) if len(sys.argv) > 1 else 132.0
        root = FloatLayout()
        self.gauge = SpeedArc(value=speed, max_value=200,
                              unit='km/h', size_hint=(1, 1))
        root.add_widget(self.gauge)
        Clock.schedule_once(self._capture, 0.8)
        return root

    def _capture(self, _dt):
        self.gauge.export_to_png('preview.png')
        Clock.schedule_once(lambda _d: self.stop(), 0.6)


if __name__ == '__main__':
    PreviewApp().run()
