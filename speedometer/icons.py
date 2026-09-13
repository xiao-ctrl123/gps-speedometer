"""矢量图标控件：用 Kivy Canvas 直接绘制，无需图标字体或图片。

用法::

    Icon(icon='speed', color=[0.3, 0.3, 0.3, 1])

支持的名称见 :data:`_ICONS`。
"""

from kivy.graphics import Color, Ellipse, Line, Rectangle, Triangle
from kivy.properties import ListProperty, StringProperty
from kivy.uix.widget import Widget


class Icon(Widget):
    icon = StringProperty('timer')
    color = ListProperty([0.3, 0.32, 0.36, 1.0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self._redraw, pos=self._redraw,
                  icon=self._redraw, color=self._redraw)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        if w <= 2 or h <= 2:
            return
        s = min(w, h)
        cx, cy = self.x + w / 2.0, self.y + h / 2.0
        draw = _ICONS.get(self.icon)
        if draw is None:
            return
        with self.canvas:
            Color(*self.color)
            draw(cx, cy, s)

    # ---- 便捷绘图 ----
    @staticmethod
    def _line(points, width, cap='round', close=False):
        Line(points=points, width=width, cap=cap, joint='round', close=close)

    def _circle(self, cx, cy, r, width):
        Line(circle=(cx, cy, r), width=width, cap='round')


# ============================================================
# 各图标的绘制函数：(cx, cy, s) -> None
# ============================================================

def _timer(cx, cy, s):
    r = s * 0.34
    Line(circle=(cx, cy, r), width=s * 0.055, cap='round')
    Line(points=[cx, cy + r, cx, cy + r * 0.55], width=s * 0.05, cap='round')
    Line(points=[cx, cy, cx + r * 0.6, cy], width=s * 0.05, cap='round')
    Line(points=[cx - s * 0.09, cy + r * 1.12, cx + s * 0.09, cy + r * 1.12],
         width=s * 0.06, cap='round')


def _bars(cx, cy, s):
    heights = [0.34, 0.56, 0.78]
    for i, hh in enumerate(heights):
        x = cx + (i - 1) * s * 0.20
        Line(points=[x, cy - s * 0.36, x, cy - s * 0.36 + s * hh],
             width=s * 0.11, cap='round')


def _speed(cx, cy, s):
    r = s * 0.34
    Line(circle=(cx, cy, r), width=s * 0.055, cap='round')
    Line(points=[cx, cy, cx + r * 0.62, cy + r * 0.62],
         width=s * 0.06, cap='round')
    Ellipse(pos=(cx - s * 0.05, cy - s * 0.05), size=(s * 0.10, s * 0.10))


def _mountain(cx, cy, s):
    base = cy - s * 0.26
    Triangle(points=[
        cx - s * 0.42, base, cx - s * 0.10, cy + s * 0.38, cx + s * 0.10, base,
    ])
    Triangle(points=[
        cx + s * 0.02, base, cx + s * 0.24, cy + s * 0.10, cx + s * 0.44, base,
    ])


def _music(cx, cy, s):
    hx1, hy1 = cx - s * 0.30, cy - s * 0.24
    hx2, hy2 = cx + s * 0.02, cy - s * 0.28
    hr = s * 0.11
    Ellipse(pos=(hx1 - hr, hy1 - hr * 0.8), size=(hr * 2, hr * 1.6))
    Ellipse(pos=(hx2 - hr, hy2 - hr * 0.8), size=(hr * 2, hr * 1.6))
    top = cy + s * 0.38
    Line(points=[hx1, hy1, hx1, top, hx2, top, hx2, hy2],
         width=s * 0.055, cap='round', joint='round')


def _lightning(cx, cy, s):
    Line(points=[
        cx + s * 0.06, cy + s * 0.44,
        cx - s * 0.22, cy - s * 0.02,
        cx + s * 0.02, cy - s * 0.02,
        cx - s * 0.10, cy - s * 0.44,
        cx + s * 0.24, cy + s * 0.10,
        cx - s * 0.02, cy + s * 0.10,
    ], width=s * 0.09, cap='round', joint='round', close=True)


def _gear(cx, cy, s):
    r = s * 0.26
    Line(circle=(cx, cy, r), width=s * 0.09, cap='round')
    Ellipse(pos=(cx - s * 0.08, cy - s * 0.08), size=(s * 0.16, s * 0.16))


def _play(cx, cy, s):
    Triangle(points=[
        cx - s * 0.22, cy - s * 0.30,
        cx - s * 0.22, cy + s * 0.30,
        cx + s * 0.30, cy,
    ])


def _pause(cx, cy, s):
    Rectangle(pos=(cx - s * 0.22, cy - s * 0.28), size=(s * 0.15, s * 0.56))
    Rectangle(pos=(cx + s * 0.07, cy - s * 0.28), size=(s * 0.15, s * 0.56))


def _next(cx, cy, s):
    Triangle(points=[
        cx - s * 0.30, cy - s * 0.28,
        cx - s * 0.30, cy + s * 0.28,
        cx + s * 0.14, cy,
    ])
    Rectangle(pos=(cx + s * 0.20, cy - s * 0.28), size=(s * 0.12, s * 0.56))


def _prev(cx, cy, s):
    Triangle(points=[
        cx + s * 0.30, cy - s * 0.28,
        cx + s * 0.30, cy + s * 0.28,
        cx - s * 0.14, cy,
    ])
    Rectangle(pos=(cx - s * 0.32, cy - s * 0.28), size=(s * 0.12, s * 0.56))


def _recenter(cx, cy, s):
    r = s * 0.28
    Line(circle=(cx, cy, r), width=s * 0.06, cap='round')
    Line(points=[cx, cy - r * 1.5, cx, cy - r * 0.6], width=s * 0.06, cap='round')
    Line(points=[cx, cy + r * 0.6, cx, cy + r * 1.5], width=s * 0.06, cap='round')
    Line(points=[cx - r * 1.5, cy, cx - r * 0.6, cy], width=s * 0.06, cap='round')
    Line(points=[cx + r * 0.6, cy, cx + r * 1.5, cy], width=s * 0.06, cap='round')
    Ellipse(pos=(cx - s * 0.06, cy - s * 0.06), size=(s * 0.12, s * 0.12))


def _plus(cx, cy, s):
    Line(points=[cx - s * 0.26, cy, cx + s * 0.26, cy],
         width=s * 0.10, cap='round')
    Line(points=[cx, cy - s * 0.26, cx, cy + s * 0.26],
         width=s * 0.10, cap='round')


def _minus(cx, cy, s):
    Line(points=[cx - s * 0.26, cy, cx + s * 0.26, cy],
         width=s * 0.10, cap='round')


_ICONS = {
    'timer': _timer,
    'bars': _bars,
    'speed': _speed,
    'mountain': _mountain,
    'music': _music,
    'lightning': _lightning,
    'gear': _gear,
    'play': _play,
    'pause': _pause,
    'next': _next,
    'prev': _prev,
    'recenter': _recenter,
    'plus': _plus,
    'minus': _minus,
}
