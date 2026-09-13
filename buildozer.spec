[app]

title = Speedometer
package.name = speedometer
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf
source.exclude_dirs = .venv, bin, build, dist, __pycache__, .git, .github, .buildozer

version = 0.1.0

# python-for-android 会自动带上这些依赖
requirements = python3,kivy==2.3.1,plyer==2.1.0,mutagen

# 横屏显示；界面按长宽比自适应
orientation = landscape
fullscreen = 1
# 常亮，避免行车途中锁屏（会申请 WAKE_LOCK 权限）
android.wakelock = True

# 定位 + 读取本地音乐
android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,INTERNET,ACCESS_NETWORK_STATE,READ_MEDIA_AUDIO,READ_EXTERNAL_STORAGE

android.api = 34
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a
android.allow_backup = True
# CI 上自动接受 SDK 许可协议
android.accept_sdk_license = True

# 使用的引导程序（Kivy + SDL2）
p4a.bootstrap = sdl2

# 如需自定义图标 / 启动图，取消注释并放入对应文件
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
