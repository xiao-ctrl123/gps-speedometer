"""全屏在线瓦片地图（高德 / GCJ-02）。

特性：
- 按当前缩放级别只请求可视范围内的瓦片，内存 + 磁盘缓存
- 支持拖动平移、按钮缩放、跟随定位
- 绘制 GPS 轨迹线与带方向的定位箭头

注意：瓦片为高德坐标（GCJ-02），传入的经纬度必须已经转换为 GCJ-02
（见 :func:`speedometer.geo.wgs84_to_gcj02`）。
"""

import io
import math
import os
import tempfile
from collections import OrderedDict

from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Ellipse, Line, Rectangle, Triangle
from kivy.network.urlrequest import UrlRequest
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
)
from kivy.uix.widget import Widget

from .geo import lonlat_to_pixel, pixel_to_lonlat, tile_url_amap

_TILE = 256
_MAX_PENDING = 8


class MapView(Widget):
    center_lat = NumericProperty(39.9042)
    center_lon = NumericProperty(116.4074)
    zoom = NumericProperty(15)
    marker_bearing = NumericProperty(0.0)
    follow = BooleanProperty(True)
    has_fix = BooleanProperty(False)

    bg_color = ListProperty([0.93, 0.94, 0.95, 1.0])
    route_color = ListProperty([0.10, 0.78, 0.48, 1.0])
    accent = ListProperty([0.23, 0.51, 0.90, 1.0])
    overlay_color = ListProperty([0.0, 0.0, 0.0, 0.0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cache = OrderedDict()
        self._pending = set()
        self._failed = set()
        self._disk = self._disk_dir()
        self._drag = None
        self._tiles = []          # 便于测试/统计
        self._route = []          # [(gcj_lat, gcj_lon)]
        self._last_route = None
        self.bind(size=self._redraw, pos=self._redraw,
                  center_lat=self._redraw, center_lon=self._redraw,
                  zoom=self._redraw, marker_bearing=self._redraw,
                  has_fix=self._redraw, bg_color=self._redraw,
                  route_color=self._redraw, accent=self._redraw)
        self._redraw()

    # ------------------------------------------------------------------
    # 缓存目录
    # ------------------------------------------------------------------
    @staticmethod
    def _disk_dir():
        app = App.get_running_app()
        base = app.user_data_dir if app is not None else os.path.join(
            tempfile.gettempdir(), 'speedometer')
        path = os.path.join(base, 'tiles')
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            path = tempfile.gettempdir()
        return path

    def _disk_path(self, z, x, y):
        d = os.path.join(self._disk, str(z), str(x))
        return os.path.join(d, '%d.png' % y)

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def update_location(self, gcj_lat, gcj_lon, bearing):
        self.marker_bearing = bearing % 360.0
        self.has_fix = True
        if self.follow:
            self.center_lat = gcj_lat
            self.center_lon = gcj_lon
        self._maybe_add_route(gcj_lat, gcj_lon)

    def recenter(self, gcj_lat, gcj_lon):
        self.follow = True
        self.center_lat = gcj_lat
        self.center_lon = gcj_lon

    def add_route_point(self, gcj_lat, gcj_lon):
        self._route.append((gcj_lat, gcj_lon))
        self._redraw()

    def clear_route(self):
        self._route = []
        self._last_route = None
        self._redraw()

    def zoom_in(self):
        self.zoom = min(18, int(round(self.zoom)) + 1)

    def zoom_out(self):
        self.zoom = max(4, int(round(self.zoom)) - 1)

    def _maybe_add_route(self, lat, lon):
        if self._last_route is None:
            self._route.append((lat, lon))
            self._last_route = (lat, lon)
            return
        dlat = lat - self._last_route[0]
        dlon = lon - self._last_route[1]
        # 约 5 米：纬度 1 度 ≈ 111320 m
        if (dlat * dlat + dlon * dlon) ** 0.5 > 5.0 / 111320.0:
            self._route.append((lat, lon))
            self._last_route = (lat, lon)

    # ------------------------------------------------------------------
    # 触摸：拖动平移
    # ------------------------------------------------------------------
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._drag = (touch.x, touch.y)
            return True
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is not self or self._drag is None:
            return False
        dx = touch.x - self._drag[0]
        dy = touch.y - self._drag[1]
        self._drag = (touch.x, touch.y)
        z = int(round(self.zoom))
        world = _TILE * (2 ** z)
        px, py = lonlat_to_pixel(self.center_lon, self.center_lat, z)
        px -= dx
        py += dy
        px = min(max(px, 0.0), world)
        py = min(max(py, 0.0), world)
        self.follow = False
        self.center_lon, self.center_lat = pixel_to_lonlat(px, py, z)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._drag = None
            return True
        return False

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        if w <= 4 or h <= 4:
            return

        z = int(round(self.zoom))
        ox, oy = self.pos
        with self.canvas:
            Color(*self.bg_color)
            Rectangle(pos=self.pos, size=self.size)

            px, py = lonlat_to_pixel(self.center_lon, self.center_lat, z)
            left = px - w / 2.0
            top = py - h / 2.0
            x0 = int(math.floor(left / _TILE))
            y0 = int(math.floor(top / _TILE))
            x1 = int(math.floor((left + w) / _TILE))
            y1 = int(math.floor((top + h) / _TILE))
            n = 2 ** z
            self._tiles = []
            for tx in range(x0, x1 + 1):
                for ty in range(y0, y1 + 1):
                    if ty < 0 or ty >= n:
                        continue
                    self._tiles.append((z, tx, ty))
                    spot = (ox + tx * _TILE - left,
                            oy + h - (ty * _TILE - top) - _TILE)
                    tex = self._get_tile(z, tx, ty)
                    if tex is not None:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=tex, pos=spot,
                                  size=(_TILE, _TILE))
                    else:
                        Color(*self.bg_color)
                        Rectangle(pos=spot, size=(_TILE, _TILE))

            self._draw_route(ox, oy, left, top, h, z)
            if self.has_fix:
                self._draw_marker(ox + w / 2.0, oy + h / 2.0,
                                  min(w, h) * 0.05)
            if self.overlay_color[3] > 0:
                Color(*self.overlay_color)
                Rectangle(pos=self.pos, size=self.size)

    def _draw_route(self, ox, oy, left, top, h, z):
        if len(self._route) < 2:
            return
        pts = []
        for lat, lon in self._route:
            rx, ry = lonlat_to_pixel(lon, lat, z)
            sx = ox + rx - left
            sy = oy + h - (ry - top)
            if (-2000 <= sx <= 2000 + self.width
                    and -2000 <= sy <= 2000 + self.height):
                pts.extend([sx, sy])
        if len(pts) >= 4:
            Color(*self.route_color)
            Line(points=pts, width=max(3.0, min(self.size) * 0.006),
                 cap='round', joint='round')

    def _draw_marker(self, cx, cy, r):
        ang = math.radians(self.marker_bearing)

        def pt(dist, offset_deg):
            a = ang + math.radians(offset_deg)
            return (cx + dist * math.sin(a), cy + dist * math.cos(a))

        tip = pt(r * 1.5, 0)
        left = pt(r * 1.0, 145)
        right = pt(r * 1.0, -145)
        notch = pt(r * 0.45, 180)

        Color(1, 1, 1, 0.9)
        Ellipse(pos=(cx - r * 1.7, cy - r * 1.7),
                size=(r * 3.4, r * 3.4))
        Color(*self.accent)
        Triangle(points=[tip[0], tip[1], left[0], left[1],
                         notch[0], notch[1]])
        Triangle(points=[tip[0], tip[1], right[0], right[1],
                         notch[0], notch[1]])

    # ------------------------------------------------------------------
    # 瓦片加载
    # ------------------------------------------------------------------
    def _get_tile(self, z, x, y):
        key = (z, x, y)
        tex = self._cache.get(key)
        if tex is not None:
            return tex

        path = self._disk_path(z, x, y)
        if os.path.exists(path):
            try:
                tex = CoreImage(path).texture
                self._cache[key] = tex
                if len(self._cache) > 400:
                    self._cache.popitem(last=False)
                return tex
            except Exception:
                pass

        self._request_tile(z, x, y, path)
        return None

    def _request_tile(self, z, x, y, path):
        key = (z, x, y)
        if key in self._pending or key in self._failed:
            return
        if len(self._pending) >= _MAX_PENDING:
            return
        self._pending.add(key)
        sub = (x + y) % 4 + 1
        url = tile_url_amap(z, x, y, subdomain=sub)

        def _fail(*_a):
            self._pending.discard(key)
            self._failed.add(key)
            self._redraw()

        UrlRequest(url, on_success=self._on_tile, on_failure=_fail,
                   on_error=_fail, timeout=12,
                   req_headers={'User-Agent': 'Mozilla/5.0 Speedometer/0.1'})

    def _on_tile(self, request, result):
        # 从请求里反推 key 不方便，改用 UrlRequest 保存的 url 解析
        z, x, y = self._parse_url(request.url)
        key = (z, x, y)
        self._pending.discard(key)
        if z is None:
            return
        try:
            data = result
            if isinstance(data, str):
                data = data.encode('latin-1')
            image = CoreImage(io.BytesIO(data), ext='png')
            texture = image.texture
        except Exception:
            self._failed.add(key)
            return
        self._cache[key] = texture
        if len(self._cache) > 400:
            self._cache.popitem(last=False)
        self._save_disk(z, x, y, data)
        self._redraw()

    def _save_disk(self, z, x, y, data):
        path = self._disk_path(z, x, y)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as fh:
                fh.write(data)
        except OSError:
            pass

    @staticmethod
    def _parse_url(url):
        try:
            q = url.split('?', 1)[1]
            parts = dict(
                p.split('=', 1) for p in q.split('&') if '=' in p)
            return int(parts['z']), int(parts['x']), int(parts['y'])
        except Exception:
            return None, None, None
