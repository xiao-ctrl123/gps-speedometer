"""Canvas 绘制公共工具：极坐标、圆弧采样、文本纹理缓存。"""

import math

from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle

_text_cache = {}


def polar(cx, cy, radius, degrees):
    rad = math.radians(degrees)
    return cx + radius * math.cos(rad), cy + radius * math.sin(rad)


def arc_points(cx, cy, radius, angle_start, angle_end, max_steps=180):
    span = angle_end - angle_start
    steps = max(2, min(max_steps, int(abs(span) / 2.0) + 1))
    pts = []
    for i in range(steps + 1):
        a = angle_start + span * i / steps
        pts.extend(polar(cx, cy, radius, a))
    return pts


def text_texture(text, font_size, color, bold=False, font_name=None):
    key = (text, int(round(font_size)),
           tuple(round(c, 3) for c in color), bold, font_name)
    tex = _text_cache.get(key)
    if tex is None:
        kwargs = dict(text=text, font_size=font_size,
                      color=list(color), bold=bold)
        if font_name:
            kwargs['font_name'] = font_name
        label = CoreLabel(**kwargs)
        label.refresh()
        tex = label.texture
        if len(_text_cache) > 300:
            _text_cache.clear()
        _text_cache[key] = tex
    return tex


def draw_text(center_x, center_y, text, font_size, color, bold=False,
              font_name=None):
    tex = text_texture(text, font_size, color, bold, font_name)
    Color(1, 1, 1, 1)
    Rectangle(texture=tex,
              pos=(center_x - tex.width / 2.0, center_y - tex.height / 2.0),
              size=tex.size)


def text_size(text, font_size, bold=False, font_name=None):
    tex = text_texture(text, font_size, [1, 1, 1, 1], bold, font_name)
    return tex.size
