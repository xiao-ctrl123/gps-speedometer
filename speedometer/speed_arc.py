"""半圆车速表（左下角）。

上半圆为 0 ~ max 的刻度弧，指针 + 中央数字读数。
"""

from kivy.graphics import Color, Ellipse, Line
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget

from .canvasutil import arc_points, draw_text, polar


class SpeedArc(Widget):
    value = NumericProperty(0.0)
    max_value = NumericProperty(200.0)
    major_step = NumericProperty(20.0)
    minor_step = NumericProperty(10.0)
    unit = StringProperty('km/h')
    start_angle = NumericProperty(180.0)
    sweep_angle = NumericProperty(180.0)

    panel_color = ListProperty([1, 1, 1, 0.95])
    border_color = ListProperty([0, 0, 0, 0.06])
    track_color = ListProperty([0.85, 0.86, 0.88, 1])
    progress_color = ListProperty([0.09, 0.78, 0.60, 1])
    tick_color = ListProperty([0.55, 0.57, 0.61, 1])
    label_color = ListProperty([0.35, 0.37, 0.41, 1])
    needle_color = ListProperty([0.90, 0.20, 0.18, 1])
    value_color = ListProperty([0.13, 0.14, 0.16, 1])
    unit_color = ListProperty([0.45, 0.47, 0.51, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            size=self._redraw, pos=self._redraw, value=self._redraw,
            max_value=self._redraw, major_step=self._redraw,
            minor_step=self._redraw, unit=self._redraw,
            panel_color=self._redraw, border_color=self._redraw,
            track_color=self._redraw, progress_color=self._redraw,
            tick_color=self._redraw, label_color=self._redraw,
            needle_color=self._redraw, value_color=self._redraw,
            unit_color=self._redraw,
        )

    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        if w <= 8 or h <= 8:
            return
        size = min(w, h)
        cx = self.x + w / 2.0
        cy = self.y + h / 2.0
        r = size * 0.46
        vmax = self.max_value or 1.0

        with self.canvas:
            # 白色圆形底板
            Color(*self.panel_color)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(*self.border_color)
            Line(circle=(cx, cy, r), width=max(1.0, size * 0.006))

            # 轨道
            Color(*self.track_color)
            track_r = r * 0.82
            Line(points=arc_points(cx, cy, track_r, self.start_angle,
                                   self.start_angle - self.sweep_angle),
                 width=max(2.0, size * 0.028), cap='round', joint='round')

            # 刻度 + 数字
            n_minor = max(1, int(round(vmax / self.minor_step)))
            ratio = max(1, int(round(self.major_step / self.minor_step)))
            for i in range(n_minor + 1):
                value = i * self.minor_step
                frac = value / vmax
                angle = self.start_angle - self.sweep_angle * frac
                major = (i % ratio == 0)
                r_out = r * 0.78
                r_in = r * (0.69 if major else 0.74)
                x1, y1 = polar(cx, cy, r_in, angle)
                x2, y2 = polar(cx, cy, r_out, angle)
                Color(*self.tick_color)
                Line(points=[x1, y1, x2, y2],
                     width=max(1.0, size * (0.006 if major else 0.003)),
                     cap='round')

            for i in range(0, n_minor + 1, ratio):
                value = i * self.minor_step
                frac = value / vmax
                angle = self.start_angle - self.sweep_angle * frac
                lx, ly = polar(cx, cy, r * 0.65, angle)
                draw_text(lx, ly, '%d' % int(round(value)),
                          size * 0.040, self.label_color, bold=True)

            # 进度弧
            frac = min(1.0, max(0.0, self.value / vmax))
            if frac >= 0.006:
                angle_now = self.start_angle - self.sweep_angle * frac
                Color(*self.progress_color)
                Line(points=arc_points(cx, cy, track_r, self.start_angle,
                                       angle_now),
                     width=max(2.0, size * 0.028), cap='round',
                     joint='round')

            # 指针
            angle = self.start_angle - self.sweep_angle * frac
            tip = polar(cx, cy, r * 0.66, angle)
            half = size * 0.012
            b1 = polar(cx, cy, half, angle + 90)
            b2 = polar(cx, cy, half, angle - 90)
            Color(*self.needle_color)
            Line(points=[b1[0], b1[1], tip[0], tip[1], b2[0], b2[1]],
                 close=True)
            Ellipse(pos=(cx - size * 0.022, cy - size * 0.022),
                    size=(size * 0.044, size * 0.044))

            # 数字读数
            draw_text(cx, cy - r * 0.20, '%d' % int(round(self.value)),
                      size * 0.24, self.value_color, bold=True)
            draw_text(cx, cy - r * 0.44, self.unit,
                      size * 0.072, self.unit_color)
