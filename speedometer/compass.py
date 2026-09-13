"""底部罗盘刻度条。

以当前航向为屏幕中心，左右各显示约 60°，每 5° 一个刻度、每 15° 一个标注，
整 45° 显示方位汉字（北/东北/东...）。
"""

from kivy.graphics import Color, Line
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.widget import Widget

from .canvasutil import draw_text

_CARDINALS = {
    0: '北', 45: '东北', 90: '东', 135: '东南',
    180: '南', 225: '西南', 270: '西', 315: '西北',
}


def cardinal_name(heading):
    idx = int(round((heading % 360) / 45.0)) * 45 % 360
    return _CARDINALS.get(idx, '北')


class CompassStrip(Widget):
    heading = NumericProperty(0.0)
    span = NumericProperty(90.0)    # 可见角度范围

    line_color = ListProperty([0, 0, 0, 0.15])
    tick_color = ListProperty([0.45, 0.47, 0.51, 1.0])
    label_color = ListProperty([0.35, 0.37, 0.41, 1.0])
    marker_color = ListProperty([0.90, 0.20, 0.18, 1.0])
    heading_color = ListProperty([0.13, 0.14, 0.16, 1.0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self._redraw, pos=self._redraw, heading=self._redraw,
                  line_color=self._redraw, tick_color=self._redraw,
                  label_color=self._redraw, marker_color=self._redraw,
                  heading_color=self._redraw)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        if w <= 8 or h <= 8:
            return
        x0 = self.x
        cx = self.x + w / 2.0
        baseline = self.y + h * 0.78
        ppd = w / float(self.span or 120.0)

        with self.canvas:
            Color(*self.line_color)
            Line(points=[x0, baseline, x0 + w, baseline],
                 width=max(1.0, h * 0.012))

            for deg in range(0, 360, 5):
                delta = ((deg - self.heading + 180) % 360) - 180
                x = cx + delta * ppd
                if x < x0 - 30 or x > x0 + w + 30:
                    continue
                major = (deg % 15 == 0)
                length = h * (0.26 if major else 0.13)
                Color(*self.tick_color)
                Line(points=[x, baseline, x, baseline - length],
                     width=max(1.0, h * (0.018 if major else 0.010)),
                     cap='round')

                if deg % 15 != 0:
                    continue
                name = _CARDINALS.get(deg)
                if name:
                    label = name
                    fs = h * 0.20
                else:
                    label = '%d' % deg
                    fs = h * 0.185
                draw_text(x, baseline - h * 0.40, label, fs,
                          self.label_color, bold=bool(name))

            # 当前航向标记
            Color(*self.marker_color)
            Line(points=[cx, baseline + h * 0.04, cx, baseline - h * 0.34],
                 width=max(2.0, h * 0.030), cap='round')

            draw_text(cx, self.y + h * 0.13,
                      '%.0f° %s' % (self.heading % 360,
                                    cardinal_name(self.heading)),
                      h * 0.22, self.heading_color, bold=True)
