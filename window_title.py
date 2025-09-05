import ctypes
from ctypes import wintypes
import win32gui
import win32process
import psutil

# WinAPI 常量
EVENT_OBJECT_NAMECHANGE = 0x800C
WINEVENT_OUTOFCONTEXT = 0

user32 = ctypes.windll.user32

# 定义 WinEventProc 回调类型
WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,  # hWinEventHook
    wintypes.DWORD,   # event
    wintypes.HWND,    # hwnd
    wintypes.LONG,    # idObject
    wintypes.LONG,    # idChild
    wintypes.DWORD,   # dwEventThread
    wintypes.DWORD    # dwmsEventTime
)

class WindowTitleWatcher:
    def __init__(self, process_name, on_title_change):
        """
        :param process_name: 目标进程名，例如 "cloudmusic.exe"
        :param on_title_change: 回调函数，签名为 callback(title: str)
        """
        self.process_name = process_name.lower()
        self.on_title_change = on_title_change
        self.hook = None
        self._proc_ref = None  # 保存回调引用，防止被GC

    def _callback(self, hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
        if idObject != 0:  # 只关心窗口本身
            return
        if win32gui.IsWindowVisible(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                if proc.name().lower() == self.process_name:
                    title = win32gui.GetWindowText(hwnd)
                    self.on_title_change(title)
            except psutil.NoSuchProcess:
                pass

    def start(self):
        """启动监听"""
        self._proc_ref = WinEventProcType(self._callback)
        self.hook = user32.SetWinEventHook(
            EVENT_OBJECT_NAMECHANGE,
            EVENT_OBJECT_NAMECHANGE,
            0,
            self._proc_ref,
            0,
            0,
            WINEVENT_OUTOFCONTEXT
        )

        # 消息循环
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self):
        """停止监听"""
        if self.hook:
            user32.UnhookWinEvent(self.hook)
            self.hook = None

# =========================
# 使用示例
# =========================
if __name__ == "__main__":
    def on_change(title):
        print("标题变化:", title)

    watcher = WindowTitleWatcher("cloudmusic.exe", on_change)
    watcher.start()