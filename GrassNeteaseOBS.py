import obspython as obs
import ctypes
import psutil
import struct
import requests
import json
import time
import os
import threading
import win32gui
import win32process
from pymem import Pymem
from pymem.process import module_from_name
import threading
from concurrent.futures import ThreadPoolExecutor
"""
网易云音乐OBS插件 - 实时显示当前播放歌曲信息

功能:
- 自动获取网易云音乐当前播放歌曲信息
- 支持歌词显示（含翻译）
- 支持播放进度显示
- 支持封面下载
- 通过OBS文本源和图片源显示内容

配置项:
- refresh_interval: 刷新间隔(毫秒)
- song_title_path: 歌曲标题输出路径
- progress_path: 进度输出路径
- lyric_path: 歌词输出路径
- cover_path: 封面保存路径
- enable_lyrics: 是否启用歌词
- enable_translation: 是否启用翻译
- enable_progress: 是否启用进度
- enable_cover: 是否启用封面
- subtitle_offset_ms: 字幕时间偏移(毫秒)
- progress_format: 进度显示格式(mm:ss或percent)

依赖:
- obspython (OBS Python脚本支持)
- pymem (内存读取)
- psutil (进程管理)
- requests (网络请求)
- win32gui (窗口管理)

作者: liubiliGrass
"""

# ===================== 线程池 & 函数定义 ========================
# 用于执行耗时的搜索、歌词与封面下载
executor = ThreadPoolExecutor(max_workers=3)

# ======================== 配置项 ========================
refresh_interval = 1000  # 刷新间隔（毫秒）

song_title_path = "C:/OBS/song_title.txt"
progress_path = "C:/OBS/progress.txt"
lyric_path = "C:/OBS/lyric.txt"
cover_path = "C:/OBS/cover.jpg"

enable_lyrics = True
enable_translation = True
enable_progress = True
enable_cover = True
subtitle_offset_ms = 0  # 字幕偏移时间（毫秒），正值为延后，负值为提前

progress_format = "mm:ss"  # 支持 mm:ss 或 percent

# ===================== 内部变量 ========================
last_song = ""
song_id_cache = None
lyric_data = None
cover_url_cache = None
cover_downloaded = False

progress_cache = -1

last_title = ""
last_title_time = 0



PROCESS_NAME = "cloudmusic.exe"
MODULE_NAME = "cloudmusic.dll"
#OFFSET_CHAIN = [0x01C6D230, 0xB8] 
OFFSET_CHAIN = [0x01C713B0, 0xB8]  # 根据实际情况调整偏移链
try:
    pm = Pymem(PROCESS_NAME)
    mod = module_from_name(pm.process_handle, MODULE_NAME)
except Exception as e:
    obs.script_log(obs.LOG_ERROR, f"初始化失败: {e}")
base = mod.lpBaseOfDll

# ===================== 函数定义 ========================

def get_window_title():

    def callback(hwnd, titles):
        if win32gui.IsWindowVisible(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['pid'] == pid and proc.info['name'].lower() == PROCESS_NAME:
                    titles.append(win32gui.GetWindowText(hwnd))
    titles = []
    win32gui.EnumWindows(callback, titles)
    return titles[0] if titles else ""

def get_window_title_cached():
    global last_title, last_title_time
    if time.time() - last_title_time > 1:
        last_title = get_window_title()
        last_title_time = time.time()
    return last_title


def extract_song_info(title):
    if " - " in title:
        parts = title.split(" - ")
        return parts[0].strip(), parts[1].strip()
    return title.strip(), ""
def split_artists(artist_field: str) -> list[str]:
    # 支持 “/”、“&”、“，” 等分隔
    import re
    parts = re.split(r'[\/&,、]+', artist_field)
    return [p.strip() for p in parts if p.strip()]

def search_song(song_name, artist):
    global song_id_cache, cover_url_cache
    artist_list = split_artists(artist)
    url = f"https://music.163.com/api/search/get"
    params = {
        's': song_name,
        'type': 1,
        'limit': 10,
        # 保留五个
        'offset': 0
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.post(url, data=params, headers=headers , timeout=2)
        results = response.json()['result']['songs']
        obs.script_log(obs.LOG_INFO, f"搜索到 {len(results)} 首歌曲")
        # obs.script_log(obs.LOG_INFO, f"完整 JSON 数据:\n{json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        obs.script_log(obs.LOG_WARNING, f"[匹配提示] 歌曲名: {song_name}, 歌手: {artist}")
        for song in results:
        # 只要候选歌手列表里任意一位匹配即可
            if any(a['name'] in artist_list or any(sub in a['name'] for sub in artist_list)
               for a in song['artists']):
                song_id_cache = song['id']
                
                obs.script_log(obs.LOG_INFO, f"找到匹配的歌曲: {song['name']} - {song['artists'][0]['name']}")
                return song_id_cache
        song_id_cache = results[0]['id']
        

        obs.script_log(obs.LOG_WARNING, f"[匹配提示] 未找到完全匹配的歌手，使用默认：{results[0]['name']}")
        return song_id_cache
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"搜索歌曲失败: {e}")
        return None

def get_lyrics(song_id):
    global lyric_data
    try:
        url = f"https://music.163.com/api/song/lyric?id={song_id}&lv=1&kv=1&tv=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=2)
        data = response.json()
        # obs.script_log(obs.LOG_INFO, f"歌词接口返回:\n{json.dumps(data, ensure_ascii=False, indent=2)}")
        main = parse_lyric(data.get("lrc", {}).get("lyric", ""))
        trans = parse_lyric(data.get("tlyric", {}).get("lyric", ""))
        lyric_data = merge_lyrics(main, trans) if enable_translation else main
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"获取歌词失败: {e}")
        lyric_data = {}

def parse_lyric(raw):
    lines = raw.strip().split("\n")
    parsed = {}
    for line in lines:
        if line.startswith("["):
            time_part = line[1:line.find("]")]
            text = line[line.find("]")+1:].strip()
            parts = time_part.split(":")
            if len(parts) == 2:
                try:
                    total_ms = int(parts[0])*60000 + float(parts[1])*1000
                    parsed[int(total_ms)] = text
                except:
                    continue
    return parsed

def merge_lyrics(main, trans):
    merged = {}
    for time in main:
        merged[time] = main[time]
        if time in trans:
            merged[time] += " / " + trans[time]
    return merged

def resolve_pointer_chain(pm, base, offsets):
    """解析多级偏移链，返回最终地址"""
    addr = base + offsets[0]
    try:
        raw = pm.read_bytes(addr, 8)
        addr = struct.unpack("<Q", raw)[0]
    except Exception as e:
        print(f"✖ 无法读取指针地址 0x{addr:X}: {e}")
        return -1

    for off in offsets[1:]:
        addr += off
    return addr

def get_progress():
    try:
        # print(f"[+] 模块基址 = 0x{base:X}")
        # 解析偏移链
        target_addr = resolve_pointer_chain(pm, base, OFFSET_CHAIN)
        # print(f"[+] 解析后的目标地址 = 0x{target_addr:X}")

        # 读取目标地址的 8 字节内容
        try:
            data = pm.read_bytes(target_addr, 8)
        except Exception as e:
            # print(f"✖ 读取地址 0x{target_addr:X} 失败: {e}")
            obs.log(obs.LOG_ERROR, f"读取地址 0x{target_addr:X} 失败: {e}")
            return -1

        # 打印每个字节
        # for i, b in enumerate(data):
            # print(f"[+] byte[{i}] = 0x{b:02X}")

        # 小端解析为 uint64
        val = struct.unpack("<Q", data)[0]
        # print(f"[+] 最终值 = 0x{val:X} ({val})")
        val += subtitle_offset_ms  # 应用字幕偏移

        # obs.script_log(obs.LOG_INFO, f"进度接口返回: {val} ms")
        return val
    except:
        pass
    return -1

def update_progress_cache():
    global progress_cache
    result = get_progress()
    if result >= 0:
        progress_cache = result



def module_base_address(pid, module_name):
    try:
        proc = psutil.Process(pid)
        for m in proc.memory_maps():
            if module_name.lower() in m.path.lower():
                return int(m.addr.split('-')[0], 16)
    except:
        return None

# 避免重复写入
last_written = {
    "song": "",
    "lyric": "",
    "progress": ""
}

# ✅ 新写法：避免重复写入
def write_file(path, content, key):
    global last_written
    if last_written.get(key) != content:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            last_written[key] = content
        except:
            pass
        

def download_cover():
    global cover_downloaded
    if not cover_url_cache:
        return
    try:
        data = requests.get(cover_url_cache, timeout=2).content
        with open(cover_path, 'wb') as f:
            f.write(data)
        cover_downloaded = True
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"封面下载失败: {e}")

# ===================== 主循环 ========================

def update():
    global last_song, lyric_data, cover_downloaded
    title = get_window_title_cached()
    song, artist = extract_song_info(title)
    if song != last_song:
        last_song = song
        # 立即写入文本，避免等待网络
        write_file(song_title_path, f"{song} - {artist}", "song")
        write_file(lyric_path, "", "lyric")
        lyric_data = {}  # 同时清空内存中的歌词缓存
        # 在后台执行：搜索 → 获取歌词 → 下载封面
        executor.submit(_background_fetch, song, artist)

    if enable_lyrics and lyric_data:
        now = progress_cache

        # obs.script_log(obs.LOG_INFO, f"当前进度: {now} ms")
        closest = max((t for t in lyric_data if t <= now), default=None)
        line = lyric_data.get(closest, "") if closest else ""
        write_file(lyric_path, line, "lyric")


    if enable_progress:
        now = progress_cache

        formatted = format_time(now) if progress_format == "mm:ss" else f"{now} ms"
        write_file(progress_path, formatted, "progress")



def format_time(ms):
    sec = ms // 1000
    return f"{sec//60:02}:{sec%60:02}"

def script_description():
    return "网易云 OBS 歌曲信息脚本 by liubiliGrass"

def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_path(props, "song_title_path", "歌曲名输出路径", obs.OBS_PATH_FILE, "*.txt", None)
    obs.obs_properties_add_path(props, "progress_path", "进度输出路径", obs.OBS_PATH_FILE, "*.txt", None)
    obs.obs_properties_add_path(props, "lyric_path", "歌词输出路径", obs.OBS_PATH_FILE, "*.txt", None)
    obs.obs_properties_add_path(props, "cover_path", "封面保存路径", obs.OBS_PATH_FILE, "*.png", None)
    obs.obs_properties_add_bool(props, "enable_lyrics", "启用歌词")
    obs.obs_properties_add_bool(props, "enable_translation", "启用翻译歌词")
    obs.obs_properties_add_bool(props, "enable_progress", "启用进度")
    obs.obs_properties_add_bool(props, "enable_cover", "启用封面")
    obs.obs_properties_add_text(props, "progress_format", "进度格式", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "refresh_interval", "刷新间隔(ms)", 200, 10000, 100)
    obs.obs_properties_add_int(props, "subtitle_offset_ms", "字幕时间偏移(ms)", -5000, 5000, 100)
    return props

def script_update(settings):
    global song_title_path, progress_path, lyric_path, cover_path
    global enable_lyrics, enable_translation, enable_progress, enable_cover
    global refresh_interval, progress_format

    song_title_path = obs.obs_data_get_string(settings, "song_title_path")
    progress_path = obs.obs_data_get_string(settings, "progress_path")
    lyric_path = obs.obs_data_get_string(settings, "lyric_path")
    cover_path = obs.obs_data_get_string(settings, "cover_path")
    enable_lyrics = obs.obs_data_get_bool(settings, "enable_lyrics")
    enable_translation = obs.obs_data_get_bool(settings, "enable_translation")
    enable_progress = obs.obs_data_get_bool(settings, "enable_progress")
    enable_cover = obs.obs_data_get_bool(settings, "enable_cover")
    refresh_interval = obs.obs_data_get_int(settings, "refresh_interval")
    progress_format = obs.obs_data_get_string(settings, "progress_format")
    subtitle_offset_ms = obs.obs_data_get_int(settings, "subtitle_offset_ms")

    obs.timer_remove(update)
    obs.timer_add(update, refresh_interval)
    obs.timer_add(lambda: executor.submit(update_progress_cache), refresh_interval)


def script_unload():
    obs.timer_remove(update)

def _background_fetch(song, artist):
    """
    后台线程执行：
    1) search_song
    2) get_lyrics
    3) download_cover
    """
    global song_id_cache, cover_url_cache, lyric_data, cover_downloaded

    song_id = search_song(song, artist)
    if not song_id:
        return

    # 拉取歌词（网络 I/O）
    get_lyrics(song_id)

    # 下载封面（可选网络 I/O）
    if enable_cover:
        cover_downloaded = False
        download_cover()