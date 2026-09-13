# 车速仪表盘（Speedometer）

基于 **Kivy + 高德在线地图 + GPS** 的 Android 车速仪表盘，浅色地图仪表风格，
内置本地音乐播放器。所有图形（表盘、彩色环、罗盘、图标）均用 Kivy Canvas
矢量绘制，不依赖图片资源。

桌面端没有 GPS，会自动切换到**模拟数据**，方便直接运行调试界面。

## 界面元素

- **全屏在线地图**：高德瓦片（GCJ-02），显示 GPS 轨迹线与带方向的定位箭头，
  可拖动平移、按钮缩放、一键回到当前位置
- **顶部**：日期时间 + 四项行程统计（时长 / 里程 / 平均车速 / 最高车速，带图标）
- **右上**：海拔
- **左下**：半圆车速表（指针 + 数字读数，超速区自动变色）
- **右下**：本地音乐播放器（专辑封面、彩色渐变环显示播放进度、上一首/播放/下一首、进度条）
- **底部**：罗盘刻度条（每 5° 刻度、每 15° 标注、方位汉字、当前航向）
- **浅色 / 暗色主题**一键切换（左上齿轮按钮）

## 目录结构

```
GPS/
├── main.py                 # 应用入口
├── preview.py              # 开发用：导出半圆表 PNG
├── speedometer.kv          # 界面布局
├── buildozer.spec          # Android 打包配置
├── requirements.txt
└── speedometer/
    ├── app.py              # 主应用：行程统计、时钟、主题、权限、交互
    ├── mapview.py          # 在线瓦片地图（下载/缓存/平移/轨迹/箭头）
    ├── geo.py              # GCJ-02 转换 + Web Mercator 瓦片数学
    ├── speed_arc.py        # 半圆车速表
    ├── gradient_ring.py    # 彩色渐变进度环
    ├── compass.py          # 罗盘刻度条
    ├── music.py            # 本地音乐扫描与播放
    ├── icons.py            # 矢量图标（时钟/里程/车速/山/音符/播放...）
    ├── progress.py         # 细进度条
    ├── theme.py            # 浅色 / 暗色调色板
    ├── canvasutil.py       # Canvas 绘制工具（极坐标/圆弧/文本缓存）
    ├── gps.py              # GPS 数据源（Android 真实 / 桌面模拟）
    └── fonts.py            # 跨平台中文字体注册
```

## 一、桌面运行（先验证界面与逻辑）

> 需要 **Python 3.12 或 3.13**。Kivy 2.3.1 尚未提供 Python 3.14 的预编译包。

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

桌面端速度为模拟数据；地图使用高德在线瓦片（需联网）。单独预览半圆表：

```powershell
.\.venv\Scripts\python.exe preview.py 132   # 生成 preview.png
```

## 二、打包成 Android APK

`buildozer` 只能在 **Linux / macOS / WSL** 上运行，推荐 WSL2 + Ubuntu。

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip \
    autoconf libtool pkg-config zlib1g-dev libncurses5-dev \
    libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev

pip3 install --user buildozer cython virtualenv
export PATH=$PATH:~/.local/bin

buildozer -v android debug          # 首次会下载 SDK/NDK，耗时较长
buildozer android debug deploy run  # 连接手机后直接安装运行
```

产物在 `bin/` 下，例如 `bin/speedometer-0.1.0-debug.apk`。

首次启动会依次申请**定位**与**读取音频**权限。

## 三、自定义

| 想修改的内容 | 位置 |
| --- | --- |
| 半圆表量程（默认 km/h 200 / mph 130） | `speedometer/app.py` 的 `_get_arc_max` |
| 表盘配色、刻度间距 | `speedometer/speed_arc.py` |
| 渐变环色带 | `speedometer/gradient_ring.py` 的 `_STOPS` |
| 罗盘可见角度范围 | `speedometer/compass.py` 的 `span` |
| 地图缩放范围 / 瓦片源 | `speedometer/mapview.py`、`speedometer/geo.py` |
| 界面布局、文案 | `speedometer.kv` |
| 浅色 / 暗色配色 | `speedometer/theme.py` |
| 横竖屏 | `buildozer.spec` 的 `orientation` |

## 四、注意事项

- **地图坐标**：高德瓦片是 GCJ-02（火星坐标），代码已用
  `geo.wgs84_to_gcj02` 将 GPS 的 WGS-84 转换后再绘制，避免偏移。
- **瓦片版权**：地图数据版权归高德所有，界面已标注
  “地图 © 高德地图”，请勿用于商业用途或高频抓取。OSM / CartoDB 在国内
  网络下无法直连，故默认使用高德瓦片。
- **音乐播放**：依赖 `Kivy SoundLoader`（Android 上为 SDL2_mixer，支持
  mp3/ogg/wav 等），专辑封面通过 `mutagen` 读取内嵌图片；未找到音乐时
  面板显示占位状态。
- **Python 版本**：请勿使用 Python 3.14，Kivy 无对应 wheel。
- **国内网络**：`pip install` 建议使用镜像源，否则官方 CDN 可能卡住。
