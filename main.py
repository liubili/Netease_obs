import obspython as obs
import re
import win32gui
import win32process
import requests
from lxml import etree
import psutil
import time

# 默认参数（可在 OBS 设置中修改）
refresh_rate = 5  # 刷新间隔（秒）
enable_cover = True  # 是否启用封面获取
debug_mode = False  # 是否输出所有窗口标题
txt_file = "F:\\Program Files\\Netmusic\\song.txt"  # OBS 读取的文件路径
cover_file = "F:\\Program Files\\Netmusic\\cover.jpg"  # 封面图片路径
custom_prefix = "当前播放"  # 可自定义前缀，OBS参数可调整

# 1. 获取网易云音乐窗口标题，并支持 debug 模式输出所有窗口标题
def get_netease_music_title():
    def callback(hwnd, titles):
        if win32gui.IsWindowVisible(hwnd):
            class_name = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
            tid, pid = win32process.GetWindowThreadProcessId(hwnd)

            try:
                p = psutil.Process(pid)
                process_name = p.name().lower()
                window_info = f"[PID: {pid}] [{process_name}] {title}"

                if debug_mode:  # 如果启用 debug，则输出所有窗口信息
                    print(window_info)

                # 只查找网易云音乐窗口
                if process_name == "cloudmusic.exe" and title:
                    titles.append(title)
            except Exception:
                pass

    titles = []
    win32gui.EnumWindows(callback, titles)
    return titles[0] if titles else None

# 2. 解析歌曲信息（根据 debug_mode 返回不同内容）
def extract_song_info(title):
    if debug_mode:
        # debug模式下返回完整信息
        return title
    else:
        # 正常模式下只返回歌曲名部分
        pattern = r"\] (.+)$"
        match = re.search(pattern, title)
        return match.group(1) if match else title

# 3. 获取网易云音乐封面（爬取）
def get_song_cover(song_name):
    search_url = f"https://music.163.com/#/search/m/?s={song_name}&type=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(search_url, headers=headers)
    html = etree.HTML(response.text)

    cover_url = html.xpath('//img/@data-src')
    return cover_url[0] if cover_url else None

# 4. 下载封面图片
def download_cover(cover_url, file_name=cover_file):
    if cover_url:
        response = requests.get(cover_url)
        with open(file_name, "wb") as f:
            f.write(response.content)

# 5. 保存数据到 OBS 读取的文件
def save_to_file(song_info, cover_url):
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(f"{custom_prefix}：{song_info}")
    if cover_url:
        download_cover(cover_url)

# 6. 让 OBS 生成可调参数
def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(props, "custom_prefix", "歌曲信息前缀", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "refresh_rate", "刷新间隔（秒）", 1, 10, 1)
    obs.obs_properties_add_bool(props, "enable_cover", "启用封面获取")
    obs.obs_properties_add_bool(props, "debug_mode", "开启 Debug 模式（显示所有窗口标题）")
    obs.obs_properties_add_path(props, "txt_file", "文件路径", obs.OBS_PATH_FILE, "*.txt;*.log;*", None)
    obs.obs_properties_add_path(props, "cover_file", "封面路径", obs.OBS_PATH_FILE, "*.jpg;*.png;*", None)
    return props

def script_update(settings):
    global refresh_rate, enable_cover, debug_mode, txt_file, cover_file, custom_prefix
    refresh_rate = obs.obs_data_get_int(settings, "refresh_rate")
    enable_cover = obs.obs_data_get_bool(settings, "enable_cover")
    debug_mode = obs.obs_data_get_bool(settings, "debug_mode")
    txt_file = obs.obs_data_get_string(settings, "txt_file")
    cover_file = obs.obs_data_get_string(settings, "cover_file")
    custom_prefix = obs.obs_data_get_string(settings, "custom_prefix") or "当前播放"

    print(f"当前设置: 刷新间隔={refresh_rate}, 封面获取={enable_cover}, Debug模式={debug_mode}")
    print(f"文件路径={txt_file}, 封面路径={cover_file}, 歌曲前缀={custom_prefix}")

# 8. 自动更新 OBS 信息
def main_loop():
    title = get_netease_music_title()
    if title:
        song_info = extract_song_info(title)
        cover_url = get_song_cover(song_info) if enable_cover else None
        save_to_file(song_info, cover_url)
        print(f"更新成功: {song_info}")
    else:
        print("未检测到网易云音乐窗口")

obs.timer_add(main_loop, refresh_rate * 1000)