"""彩色渐变进度环（右下角，围绕专辑封面）。

按绿色 -> 黄 -> 橙 -> 红的固定色带绘制进度，剩余部分为灰色。
"""

from kivy.graphics import Color, Line
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.widget import Widget

from .canvasutil import polar

# (位置 0-1, RGBA)
_STOPS = [
    (0.00, (0.20, 0.85, 0.45, 1.0)),
    (0.35, (0.65, 0.90, 0.25, 1.0)),
    (0.60, (0.98, 0.85, 0.16, 1.0)),
    (0.80, (0.99, 0.60, 0.13, 1.0)),
    (1.00, (0.92, 0.20, 0.16, 1.0)),
]


def _gradient(t):
    t = min(1.0, max(0.0, t))
    for i in range(len(_STOPS) - 1):
        p0, c0 = _STOPS[i]
        p1, c1 = _STOPS[i + 1]
        if t <= p1:
            k = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return [c0[j] + (c1[j] - c0[j]) * k for j in range(4)]
    return list(_STOPS[-1][1])


class GradientRing(Widget):
    fraction = NumericProperty(0.0)
    start_angle = NumericProperty(90.0)
    sweep = NumericProperty(360.0)
    thickness = NumericProperty(0.13)     # 相对半径
    segments = NumericProperty(72)

    off_color = ListProperty([0.55, 0.57, 0.62, 0.35])
    bg_color = ListProperty([0.0, 0.0, 0.0, 0.0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self._redraw, pos=self._redraw,
                  fraction=self._redraw, off_color=self._redraw,
                  thickness=self._redraw, bg_color=self._redraw,
                  start_angle=self._redraw)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        if w <= 8 or h <= 8:
            return
        size = min(w, h)
        cx = self.x + w / 2.0
        cy = self.y + h / 2.0
        radius = size * 0.45
        width = max(2.0, radius * 2 * self.thickness * 0.5)

        frac = min(1.0, max(0.0, self.fraction))
        n = max(8, int(self.segments))
        per = self.sweep / n

        with self.canvas:
            if self.bg_color[3] > 0:
                Color(*self.bg_color)
                Line(circle=(cx, cy, radius), width=width)

            # 未完成部分
            if frac < 1.0:
                Color(*self.off_color)
                a0 = self.start_angle - self.sweep * frac
                a1 = self.start_angle - self.sweep
                Line(points=self._arc(cx, cy, radius, a0, a1),
                     width=width, cap='round', joint='round')

            # 已完成部分：分段渐变
            steps = int(round(n * frac))
            for i in range(max(0, steps)):
                t0 = i / float(n)
                t1 = (i + 1) / float(n)
                mid = (t0 + t1) / 2.0
                Color(*_gradient(mid))
                a0 = self.start_angle - self.sweep * t0
                a1 = self.start_angle - self.sweep * t1
                Line(points=self._arc(cx, cy, radius, a0, a1),
                     width=width, cap='round', joint='round')

    @staticmethod
    def _arc(cx, cy, r, a0, a1):
        span = a1 - a0
        steps = max(3, int(abs(span) / 3.0) + 1)
        pts = []
        for i in range(steps + 1):
            pts.extend(polar(cx, cy, r, a0 + span * i / steps))
        return pts
