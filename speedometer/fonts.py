"""跨平台中文字体注册。

Kivy 自带的 Roboto 字体不包含中文字形，会导致中文显示成方块。
这里在系统字体目录中寻找一个可用的中文字体，注册为默认字体名
``Roboto``，这样所有控件的 ``font_name`` 无需单独修改。
"""

import os

from kivy.core.text import LabelBase
from kivy.utils import platform

# 各平台常见的中文字体路径，按优先级排列。
_CANDIDATES = {
    'win': [
        r'C:\Windows\Fonts\msyh.ttc',
        r'C:\Windows\Fonts\msyhbd.ttc',
        r'C:\Windows\Fonts\simhei.ttf',
        r'C:\Windows\Fonts\simsun.ttc',
    ],
    'android': [
        '/system/fonts/NotoSansCJK-Regular.ttc',
        '/system/fonts/NotoSansCJKsc-Regular.otf',
        '/system/fonts/DroidSansFallback.ttf',
        '/system/fonts/DroidSansFallbackFull.ttf',
        '/system/fonts/NotoSansSC-Regular.otf',
    ],
    'linux': [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/arphic/uming.ttc',
    ],
    'macosx': [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ],
}


def find_cjk_font():
    """返回系统中第一个可用的中文字体路径，找不到则返回 None。"""
    for path in _CANDIDATES.get(platform, []):
        if os.path.exists(path):
            return path
    # 兜底：某些发行版把字体放在别处，遍历常见目录
    for root in ('/usr/share/fonts', '/usr/local/share/fonts'):
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                low = name.lower()
                if low.endswith(('.ttf', '.otf', '.ttc')) and (
                        'cjk' in low or 'hei' in low or 'song' in low
                        or 'noto' in low):
                    return os.path.join(dirpath, name)
    return None


def register_cjk_font(name='Roboto'):
    """把找到的中文字体注册为 ``name``（默认覆盖 Roboto）。

    返回注册的字体路径；若未找到任何中文字体则返回 None。
    """
    path = find_cjk_font()
    if not path:
        return None
    try:
        LabelBase.register(name=name, fn_regular=path)
    except Exception:
        return None
    return path
