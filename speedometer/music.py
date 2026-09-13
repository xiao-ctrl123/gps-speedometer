"""本地音乐播放器。

- 扫描设备常见音乐目录中的音频文件
- 读取 ID3 / MP4 / FLAC 标签与内嵌专辑封面（依赖 mutagen，可选）
- 使用 Kivy ``SoundLoader`` 播放；手动计时跟踪播放进度

说明：桌面端若没有音频后端，播放会静默失败，但界面与列表仍可用。
"""

import io
import os
import threading

from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.event import EventDispatcher
from kivy.properties import (
    AliasProperty,
    BooleanProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.utils import platform

AUDIO_EXTS = ('.mp3', '.m4a', '.flac', '.ogg', '.wav', '.aac', '.wma')


def _fmt_time(seconds):
    seconds = int(seconds or 0)
    minutes, secs = divmod(seconds, 60)
    return '%02d:%02d' % (minutes, secs)


def music_dirs():
    if platform == 'android':
        return [
            '/storage/emulated/0/Music',
            '/storage/emulated/0/音乐',
            '/sdcard/Music',
            '/storage/emulated/0/Download',
            '/storage/emulated/0/Downloads',
        ]
    home = os.path.expanduser('~')
    return [os.path.join(home, 'Music'), os.path.join(home, 'Music', 'iTunes')]


def scan_music(limit=800):
    tracks = []
    for base in music_dirs():
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                if name.lower().endswith(AUDIO_EXTS):
                    tracks.append(os.path.join(dirpath, name))
                    if len(tracks) >= limit:
                        return tracks
    return tracks


def read_tags(path):
    info = {
        'path': path,
        'title': os.path.splitext(os.path.basename(path))[0],
        'artist': '',
        'album': '',
        'duration': 0.0,
    }
    try:
        from mutagen import File as MutaFile
        audio = MutaFile(path, easy=True)
        if audio is not None:
            info['title'] = _first(audio, 'title', info['title'])
            info['artist'] = _first(audio, 'artist', '')
            info['album'] = _first(audio, 'album', '')
            if getattr(audio, 'info', None) is not None:
                info['duration'] = float(audio.info.length)
    except Exception:
        pass
    return info


def _first(audio, key, default):
    try:
        values = audio.get(key)
    except Exception:
        return default
    if values:
        return str(values[0])
    return default


def read_album_art(path):
    """返回内嵌封面的原始字节，找不到返回 None。"""
    low = path.lower()
    try:
        if low.endswith('.mp3'):
            from mutagen.id3 import ID3
            tags = ID3(path)
            for key in list(tags.keys()):
                if key.startswith('APIC'):
                    return tags[key].data
        elif low.endswith(('.m4a', '.mp4', '.aac')):
            from mutagen.mp4 import MP4
            data = MP4(path).tags.get('covr')
            if data:
                return bytes(data[0])
        elif low.endswith('.flac'):
            from mutagen.flac import FLAC
            pics = FLAC(path).pictures
            if pics:
                return pics[0].data
    except Exception:
        return None
    return None


class MusicPlayer(EventDispatcher):
    tracks = ListProperty([])
    index = NumericProperty(-1)
    playing = BooleanProperty(False)
    library_ready = BooleanProperty(False)

    position = NumericProperty(0.0)     # 秒
    duration = NumericProperty(0.0)
    title = StringProperty('未找到音乐')
    artist = StringProperty('')
    album = StringProperty('')
    art_texture = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sound = None
        self._art_cache = {}
        self._ticker = None
        self._start_pos = 0.0

    # ---- 派生属性 ----
    def _get_progress(self):
        if self.duration > 0:
            return min(1.0, max(0.0, self.position / self.duration))
        return 0.0

    progress = AliasProperty(_get_progress, None,
                             bind=('position', 'duration'))

    def _get_position_text(self):
        return _fmt_time(self.position)

    position_text = AliasProperty(_get_position_text, None, bind=('position',))

    def _get_duration_text(self):
        return _fmt_time(self.duration)

    duration_text = AliasProperty(_get_duration_text, None, bind=('duration',))

    def _get_has_tracks(self):
        return len(self.tracks) > 0

    has_tracks = AliasProperty(_get_has_tracks, None, bind=('tracks',))

    def _get_play_icon(self):
        return 'pause' if self.playing else 'play'

    play_icon = AliasProperty(_get_play_icon, None, bind=('playing',))

    # ------------------------------------------------------------------
    # 库
    # ------------------------------------------------------------------
    def load_library(self):
        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()

    def _scan_worker(self):
        paths = scan_music()
        infos = [read_tags(p) for p in paths]
        Clock.schedule_once(lambda _dt: self._set_library(infos), 0)

    def _set_library(self, infos):
        self.tracks = infos
        self.library_ready = True
        if infos and self.index < 0:
            self._load_track(0, autoplay=False)

    # ------------------------------------------------------------------
    # 播放控制
    # ------------------------------------------------------------------
    def _load_track(self, index, autoplay=True):
        if not self.tracks:
            return
        index = index % len(self.tracks)
        self._stop_sound()
        self.index = index
        track = self.tracks[index]
        self.title = track['title'] or '未知曲目'
        self.artist = track['artist'] or '未知艺术家'
        self.album = track['album']
        self.duration = float(track.get('duration') or 0.0)
        self.position = 0.0
        self._art_cache = {}   # 简化：切换曲目时清空
        self._load_art(track['path'])
        if autoplay:
            self.play()

    def _load_art(self, path):
        self.art_texture = None
        data = read_album_art(path)
        if not data:
            return
        try:
            self.art_texture = CoreImage(io.BytesIO(data), ext='png').texture
        except Exception:
            self.art_texture = None

    def play(self):
        if not self.tracks:
            return
        if self._sound is None:
            self._create_sound()
        if self._sound is None:
            return
        try:
            self._sound.play()
            self.playing = True
            self._start_pos = self.position
            self._start_ticker()
        except Exception:
            self.playing = False

    def _create_sound(self):
        track = self.tracks[self.index]
        try:
            self._sound = SoundLoader.load(track['path'])
        except Exception:
            self._sound = None
        if self._sound is not None and not self.duration:
            try:
                self.duration = float(self._sound.length or 0.0)
            except Exception:
                pass

    def pause(self):
        if self._sound is not None:
            try:
                self._sound.stop()
            except Exception:
                pass
        self.playing = False
        self._stop_ticker()

    def toggle(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def next(self):
        if self.tracks:
            self._load_track(self.index + 1)

    def prev(self):
        if self.tracks:
            self._load_track(self.index - 1)

    def seek_fraction(self, frac):
        if not self.duration or self._sound is None:
            return
        target = max(0.0, min(1.0, frac)) * self.duration
        try:
            self._sound.seek(target)
        except Exception:
            pass
        self.position = target
        self._start_pos = target

    # ------------------------------------------------------------------
    # 进度计时
    # ------------------------------------------------------------------
    def _start_ticker(self):
        if self._ticker is None:
            self._ticker = Clock.schedule_interval(self._tick, 0.25)

    def _stop_ticker(self):
        if self._ticker is not None:
            self._ticker.cancel()
            self._ticker = None

    def _tick(self, _dt):
        if not self.playing:
            return
        self.position += 0.25
        if self.duration and self.position >= self.duration:
            self.position = self.duration
            self.next()

    def _stop_sound(self):
        self._stop_ticker()
        if self._sound is not None:
            try:
                self._sound.stop()
            except Exception:
                pass
            self._sound = None
        self.playing = False

    def on_stop(self):
        self._stop_sound()
