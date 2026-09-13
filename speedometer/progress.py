"""细进度条（音乐播放进度）。"""

from kivy.graphics import Color, Line
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.widget import Widget


class ProgressLine(Widget):
    fraction = NumericProperty(0.0)
    track_color = ListProperty([0.0, 0.0, 0.0, 0.12])
    fill_color = ListProperty([0.23, 0.51, 0.90, 1.0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self._redraw, pos=self._redraw,
                  fraction=self._redraw, track_color=self._redraw,
                  fill_color=self._redraw)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        if w <= 2 or h <= 1:
            return
        y = self.y + h / 2.0
        width = h
        frac = min(1.0, max(0.0, self.fraction))
        with self.canvas:
            Color(*self.track_color)
            Line(points=[self.x, y, self.x + w, y],
                 width=width, cap='round')
            if frac > 0.001:
                Color(*self.fill_color)
                Line(points=[self.x, y, self.x + w * frac, y],
                     width=width, cap='round')
