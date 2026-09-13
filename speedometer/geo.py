"""地理坐标工具：GCJ-02 偏移与 Web Mercator 瓦片数学。

国内地图（高德/腾讯等）使用 GCJ-02（火星坐标），而 GPS 输出 WGS-84。
直接把 WGS-84 画到高德瓦片上会有 50~500 米偏移，因此需要先做转换。
"""

import math

_TILE_SIZE = 256
# GCJ-02 椭球参数
_A = 6378245.0
_EE = 0.00669342162296594323


def _out_of_china(lat, lon):
    return not (0.8293 <= lat <= 55.8271 and 72.004 <= lon <= 137.8347)


def _transform_lat(x, y):
    ret = (-100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y
           + 0.2 * math.sqrt(abs(x)))
    ret += (20.0 * math.sin(6.0 * x * math.pi)
            + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi)
            + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi)
            + 320.0 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lon(x, y):
    ret = (300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y
           + 0.1 * math.sqrt(abs(x)))
    ret += (20.0 * math.sin(6.0 * x * math.pi)
            + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi)
            + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi)
            + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lat, lon):
    """WGS-84 -> GCJ-02。不在中国境内时原样返回。"""
    if _out_of_china(lat, lon):
        return lat, lon
    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * math.pi
    magic = math.sin(rad_lat)
    magic = 1 - _EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrt_magic) * math.pi)
    dlon = (dlon * 180.0) / (_A / sqrt_magic * math.cos(rad_lat) * math.pi)
    return lat + dlat, lon + dlon


def lonlat_to_pixel(lon, lat, zoom, tile_size=_TILE_SIZE):
    """经纬度 -> 该缩放级别下的世界像素坐标（Web Mercator）。"""
    world = tile_size * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * world
    siny = math.sin(math.radians(lat))
    siny = min(max(siny, -0.9999), 0.9999)
    y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * world
    return x, y


def pixel_to_lonlat(x, y, zoom, tile_size=_TILE_SIZE):
    """世界像素坐标 -> 经纬度。"""
    world = tile_size * (2 ** zoom)
    lon = x / world * 360.0 - 180.0
    n = math.pi - 2.0 * math.pi * y / world
    lat = math.degrees(math.atan(math.sinh(n)))
    return lon, lat


def tile_url_amap(z, x, y, subdomain=1, style=8):
    """高德栅格瓦片地址（GCJ-02）。style=8 为路网图。"""
    return ('https://webrd0%d.is.autonavi.com/appmaptile'
            '?lang=zh_cn&size=1&scale=1&style=%d&x=%d&y=%d&z=%d'
            % (subdomain, style, x, y, z))
