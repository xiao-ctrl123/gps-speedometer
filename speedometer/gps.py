"""车速数据来源（GPS）。

对外暴露 :class:`BaseLocationProvider` 接口和 :func:`create_provider` 工厂。
Android 上使用 ``plyer.gps`` 读取系统定位；桌面端没有 GPS，使用
:class:`SimulatedProvider` 生成模拟速度，方便开发调试界面。
"""

import math
import random
import time

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import (
    BooleanProperty,
    NumericProperty,
    StringProperty,
)
from kivy.utils import platform

MPS_TO_KMH = 3.6
MPS_TO_MPH = 2.2369362920544
KM_TO_MILE = 0.621371


class BaseLocationProvider(EventDispatcher):
    """定位数据源基类。

    速度统一使用米每秒 (m/s) 存储，界面层再按单位换算。
    """

    speed = NumericProperty(0.0)        # m/s
    latitude = NumericProperty(0.0)
    longitude = NumericProperty(0.0)
    altitude = NumericProperty(0.0)     # m
    bearing = NumericProperty(0.0)      # 度，正北为 0，顺时针
    accuracy = NumericProperty(0.0)     # m
    valid = BooleanProperty(False)
    status = StringProperty('未启动')

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError


class SimulatedProvider(BaseLocationProvider):
    """桌面调试用的模拟定位源。

    用一个简单的“加速/减速逼近随机目标速度”的模型，产生比较自然的
    速度曲线，同时用航位推算更新经纬度，让界面看起来像真的在动。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._event = None
        self._speed_kmh = 0.0
        self._target_kmh = 0.0
        self._lat = 39.9042
        self._lon = 116.4074
        self._last_t = time.time()

    def start(self):
        if self._event is None:
            self._last_t = time.time()
            self._event = Clock.schedule_interval(self._update, 0.2)
        self.valid = True
        self.status = '模拟数据（桌面调试）'

    def stop(self):
        if self._event is not None:
            self._event.cancel()
            self._event = None
        self.valid = False
        self.speed = 0.0
        self.status = '已停止'

    def _update(self, _dt):
        now = time.time()
        dt = min(now - self._last_t, 0.5)
        self._last_t = now

        if random.random() < 0.04:
            self._target_kmh = random.uniform(0.0, 135.0)

        diff = self._target_kmh - self._speed_kmh
        accel = max(-40.0, min(28.0, diff * 0.9))       # km/h 每秒
        self._speed_kmh = max(0.0, self._speed_kmh + accel * dt)
        speed_kmh = max(0.0, self._speed_kmh + random.gauss(0.0, 0.5))

        self.speed = speed_kmh / MPS_TO_KMH
        self.bearing = (self.bearing + random.uniform(-3.0, 3.0)) % 360.0
        self.accuracy = random.uniform(3.0, 9.0)
        self.altitude = 45.0 + random.uniform(-1.0, 1.0)

        # 航位推算，仅用于展示经纬度
        distance = self.speed * dt
        rad = math.radians(self.bearing)
        self._lat += (distance * math.cos(rad)) / 111320.0
        self._lon += (distance * math.sin(rad)) / (
            111320.0 * max(0.2, math.cos(math.radians(self._lat))))
        self.latitude = self._lat
        self.longitude = self._lon


class AndroidGpsProvider(BaseLocationProvider):
    """基于 plyer 的 Android 定位源。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._gps = None

    def start(self):
        try:
            from plyer import gps
        except Exception as exc:  # pragma: no cover - 仅在 Android 触发
            self.status = '无法加载 GPS 模块: %s' % exc
            return
        self._gps = gps
        self.status = '正在搜索卫星...'
        try:
            gps.configure(on_location=self._on_location,
                          on_status=self._on_status)
            gps.start(minTime=500, minDistance=0)
        except Exception as exc:  # pragma: no cover
            self.status = 'GPS 启动失败: %s' % exc

    def stop(self):
        try:
            if self._gps is not None:
                self._gps.stop()
        except Exception:
            pass
        self.valid = False
        self.speed = 0.0
        self.status = '已停止'

    def _on_location(self, **kwargs):
        # plyer 的回调运行在后台线程，切回主线程更新界面属性。
        Clock.schedule_once(lambda _dt: self._apply(kwargs), 0)

    def _on_status(self, _stype, status):
        Clock.schedule_once(lambda _dt: setattr(self, 'status', str(status)), 0)

    def _apply(self, data):
        self.latitude = data.get('lat') or 0.0
        self.longitude = data.get('lon') or 0.0
        self.speed = data.get('speed') or 0.0
        self.bearing = data.get('bearing') or 0.0
        self.altitude = data.get('altitude') or 0.0
        self.accuracy = data.get('accuracy') or 0.0
        self.valid = True
        self.status = 'GPS 已定位'


def create_provider():
    """按当前平台创建合适的数据源。"""
    if platform == 'android':
        return AndroidGpsProvider()
    return SimulatedProvider()
