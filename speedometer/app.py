"""车速仪表盘主应用（浅色地图仪表风格）。"""

import datetime
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (
    AliasProperty,
    BooleanProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.floatlayout import FloatLayout
from kivy.utils import platform

from . import theme
from .compass import CompassStrip  # noqa: F401
from .fonts import register_cjk_font
from .geo import wgs84_to_gcj02
from .gradient_ring import GradientRing  # noqa: F401
from .gps import KM_TO_MILE, MPS_TO_KMH, MPS_TO_MPH, create_provider
from .icons import Icon  # noqa: F401
from .mapview import MapView  # noqa: F401
from .music import MusicPlayer
from .progress import ProgressLine  # noqa: F401
from .speed_arc import SpeedArc  # noqa: F401


class SpeedometerScreen(FloatLayout):
    """根布局，结构见 speedometer.kv。"""


def _format_duration(seconds):
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return '%d:%02d:%02d' % (hours, minutes, secs)
    return '%02d:%02d' % (minutes, secs)


class SpeedometerApp(App):
    speed_mps = NumericProperty(0.0)
    heading = NumericProperty(0.0)
    unit = StringProperty('km/h')
    recording = BooleanProperty(False)
    has_trip = BooleanProperty(False)
    is_dark = BooleanProperty(False)

    clock_text = StringProperty('')
    gps_status = StringProperty('初始化...')
    gps_valid = BooleanProperty(False)
    accuracy_text = StringProperty('--')

    altitude_text = StringProperty('海拔 --')
    max_speed_text = StringProperty('0')
    avg_speed_text = StringProperty('0')
    distance_text = StringProperty('0')
    duration_text = StringProperty('00:00')

    provider = ObjectProperty(None, allownone=True)
    music = ObjectProperty(None, allownone=True)

    # 主题色（默认浅色，build 时按 is_dark 覆盖）
    c_bg = ListProperty(list(theme.LIGHT['bg']))
    c_panel = ListProperty(list(theme.LIGHT['panel']))
    c_panel_border = ListProperty(list(theme.LIGHT['panel_border']))
    c_fg = ListProperty(list(theme.LIGHT['fg']))
    c_fg_dim = ListProperty(list(theme.LIGHT['fg_dim']))
    c_fg_faint = ListProperty(list(theme.LIGHT['fg_faint']))
    c_accent = ListProperty(list(theme.LIGHT['accent']))
    c_icon = ListProperty(list(theme.LIGHT['icon']))
    c_track = ListProperty(list(theme.LIGHT['track']))
    c_needle = ListProperty(list(theme.LIGHT['needle']))
    c_route = ListProperty(list(theme.LIGHT['route']))
    c_ring_off = ListProperty(list(theme.LIGHT['ring_off']))
    c_overlay = ListProperty([0, 0, 0, 0])

    # ---------------------------------------------------------------
    # 派生属性
    # ---------------------------------------------------------------
    def _get_speed_display(self):
        factor = MPS_TO_KMH if self.unit == 'km/h' else MPS_TO_MPH
        return self.speed_mps * factor

    speed_display = AliasProperty(_get_speed_display, None,
                                  bind=('speed_mps', 'unit'))

    def _get_arc_max(self):
        return 200.0 if self.unit == 'km/h' else 130.0

    arc_max = AliasProperty(_get_arc_max, None, bind=('unit',))

    def _get_distance_unit(self):
        return 'km' if self.unit == 'km/h' else 'mi'

    distance_unit = AliasProperty(_get_distance_unit, None, bind=('unit',))

    def _get_primary_text(self):
        if self.recording:
            return '暂停'
        return '继续' if self.has_trip else '开始'

    primary_button_text = AliasProperty(_get_primary_text, None,
                                        bind=('recording', 'has_trip'))

    # ---------------------------------------------------------------
    # 生命周期
    # ---------------------------------------------------------------
    def build(self):
        self.title = '车速仪表盘'
        register_cjk_font()
        self._load_kv_file()

        self._session_time = 0.0
        self._distance_m = 0.0
        self._max_mps = 0.0
        self._last_gcj = None

        self._apply_theme()
        self.provider = create_provider()
        self.music = MusicPlayer()

        root = SpeedometerScreen()
        self._update_clock()

        Clock.schedule_interval(self._tick, 0.1)
        Clock.schedule_interval(self._clock_tick, 1.0)
        Clock.schedule_once(lambda _dt: self._request_location(), 0.4)
        return root

    def _load_kv_file(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'speedometer.kv',
        )
        if not os.path.exists(path):
            return
        known = {os.path.abspath(f) for f in Builder.files}
        if os.path.abspath(path) not in known:
            Builder.load_file(path)

    def on_stop(self):
        if self.provider:
            self.provider.stop()
        if self.music:
            self.music.on_stop()

    def on_pause(self):
        self.recording = False
        if self.provider:
            self.provider.stop()
        if self.music:
            self.music.pause()
        return True

    def on_resume(self):
        self._request_location()

    # ---------------------------------------------------------------
    # 主题
    # ---------------------------------------------------------------
    def _apply_theme(self):
        pal = theme.palette(self.is_dark)
        self.c_bg = list(pal['bg'])
        self.c_panel = list(pal['panel'])
        self.c_panel_border = list(pal['panel_border'])
        self.c_fg = list(pal['fg'])
        self.c_fg_dim = list(pal['fg_dim'])
        self.c_fg_faint = list(pal['fg_faint'])
        self.c_accent = list(pal['accent'])
        self.c_icon = list(pal['icon'])
        self.c_track = list(pal['track'])
        self.c_needle = list(pal['needle'])
        self.c_route = list(pal['route'])
        self.c_ring_off = list(pal['ring_off'])
        self.c_overlay = [0.03, 0.04, 0.06, 0.55] if self.is_dark else [0, 0, 0, 0]

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self._apply_theme()

    # ---------------------------------------------------------------
    # 权限与启动
    # ---------------------------------------------------------------
    @staticmethod
    def _android_permissions():
        from android.permissions import Permission  # type: ignore
        perms = [Permission.ACCESS_FINE_LOCATION,
                 Permission.ACCESS_COARSE_LOCATION]
        for name in ('READ_MEDIA_AUDIO', 'READ_EXTERNAL_STORAGE'):
            perm = getattr(Permission, name, None)
            if perm is not None:
                perms.append(perm)
        return perms

    def _request_location(self):
        if platform != 'android':
            if self.provider:
                self.provider.start()
            if self.music:
                self.music.load_library()
            return
        try:
            from android.permissions import (  # type: ignore
                check_permission,
                request_permissions,
            )
        except Exception as exc:
            self.gps_status = '权限模块不可用: %s' % exc
            return

        needed = self._android_permissions()
        if all(check_permission(p) for p in needed):
            self._on_permissions_granted()
            return

        self.gps_status = '等待权限...'

        def _callback(_permissions, grants):
            def _after(_dt):
                if any(grants):
                    self._on_permissions_granted()
                else:
                    self.gps_status = '未授予定位权限'

            Clock.schedule_once(_after, 0)

        request_permissions(needed, _callback)

    def _on_permissions_granted(self):
        if self.provider:
            self.provider.start()
        if self.music:
            self.music.load_library()

    # ---------------------------------------------------------------
    # 时钟
    # ---------------------------------------------------------------
    def _clock_tick(self, _dt):
        self._update_clock()

    def _update_clock(self):
        now = datetime.datetime.now()
        self.clock_text = '%d年%d月%d日 %02d:%02d' % (
            now.year, now.month, now.day, now.hour, now.minute)

    # ---------------------------------------------------------------
    # 主循环
    # ---------------------------------------------------------------
    def _tick(self, dt):
        provider = self.provider
        if provider is None:
            return

        self.speed_mps = max(0.0, provider.speed)
        self.heading = provider.bearing % 360.0
        self.gps_valid = provider.valid
        self.gps_status = provider.status

        if provider.valid:
            self.accuracy_text = '精度 %.0f m' % provider.accuracy if provider.accuracy else '精度 --'
            self.altitude_text = '海拔 %.0f m' % provider.altitude
            gcj = wgs84_to_gcj02(provider.latitude, provider.longitude)
            self._last_gcj = gcj
            mapview = self._mapview()
            if mapview is not None:
                mapview.update_location(gcj[0], gcj[1], provider.bearing)
        else:
            self.accuracy_text = '精度 --'

        if self.recording:
            self._session_time += dt
            self._distance_m += provider.speed * dt
            self._max_mps = max(self._max_mps, provider.speed)

        self._refresh_stats()

    def _mapview(self):
        root = self.root
        if root is None:
            return None
        for child in root.children:
            if isinstance(child, MapView):
                return child
        return None

    def _refresh_stats(self):
        factor = MPS_TO_KMH if self.unit == 'km/h' else MPS_TO_MPH
        self.max_speed_text = '%.0f %s' % (self._max_mps * factor, self.unit)

        if self._session_time > 0:
            avg_mps = self._distance_m / self._session_time
        else:
            avg_mps = 0.0
        self.avg_speed_text = '%.1f %s' % (avg_mps * factor, self.unit)

        distance = self._distance_m / 1000.0
        if self.unit != 'km/h':
            distance *= KM_TO_MILE
        self.distance_text = '%.1f %s' % (distance, self.distance_unit)
        self.duration_text = _format_duration(self._session_time)

    # ---------------------------------------------------------------
    # 交互
    # ---------------------------------------------------------------
    def toggle_recording(self):
        if self.recording:
            self.recording = False
            return
        if not self.has_trip:
            self.reset_trip()
            self.has_trip = True
        self.recording = True

    def reset_trip(self):
        self.recording = False
        self.has_trip = False
        self._session_time = 0.0
        self._distance_m = 0.0
        self._max_mps = 0.0
        mapview = self._mapview()
        if mapview is not None:
            mapview.clear_route()
        self._refresh_stats()

    def toggle_unit(self):
        self.unit = 'mph' if self.unit == 'km/h' else 'km/h'
        self._refresh_stats()

    def recenter_map(self):
        mapview = self._mapview()
        if mapview is None:
            return
        if self._last_gcj:
            mapview.recenter(self._last_gcj[0], self._last_gcj[1])
        else:
            mapview.follow = True

    def map_zoom_in(self):
        mapview = self._mapview()
        if mapview:
            mapview.zoom_in()

    def map_zoom_out(self):
        mapview = self._mapview()
        if mapview:
            mapview.zoom_out()
