import win32gui
import win32con
import win32api
import os
import shutil
import stat

def robust_move(src, dst):
    if os.path.exists(src):
        try:
            os.chmod(src, stat.S_IWRITE)
        except Exception:
            pass
    shutil.move(src, dst)


def get_desktop_workerw():
    progman = win32gui.FindWindow("Progman", None)
    if progman:
        win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
    
    workerw = None
    def enum_windows_callback(hwnd, extra):
        nonlocal workerw
        shell_dll = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
        if shell_dll:
            workerw = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
        return True

    win32gui.EnumWindows(enum_windows_callback, None)
    if not workerw:
        workerw = progman
    return workerw


def attach_to_desktop(hwnd):
    try:
        workerw = get_desktop_workerw()
        if workerw:
            win32gui.SetParent(hwnd, workerw)
    except Exception as e:
        print(f"Error attaching to desktop: {e}")


def set_window_bottom(hwnd):
    try:
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        )
    except Exception:
        pass




def set_desktop_icons_visible(visible):
    progman = win32gui.FindWindow("Progman", "Program Manager")
    shell_dll = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
    list_view = win32gui.FindWindowEx(shell_dll, 0, "SysListView32", None)

    if not list_view:
        def callback(hwnd, extra):
            workerw = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
            if workerw:
                lv = win32gui.FindWindowEx(workerw, 0, "SysListView32", None)
                if lv:
                    extra.append(lv)
            return True
        
        found = []
        win32gui.EnumWindows(callback, found)
        if found:
            list_view = found[0]

    if list_view:
        cmd = win32con.SW_SHOW if visible else win32con.SW_HIDE
        win32gui.ShowWindow(list_view, cmd)


def open_file_safely(file_path):
    print(f"DEBUG [open_file_safely]: Attempting to open -> {file_path}")
    file_path = os.path.normpath(file_path)
    if not os.path.exists(file_path):
        print(f"DEBUG [open_file_safely]: ERROR! File does not exist at path: {file_path}")
        return

    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ('.lnk', '.url'):
        # For shortcuts, Wechat and other Tencent apps block execution if the parent process is python.exe.
        # Launching via explorer.exe ensures the parent process is the Windows shell itself,
        # perfectly mirroring a user double-clicking on the desktop. It also avoids cmd.exe Unicode mangling.
        try:
            print(f"DEBUG [open_file_safely]: Using explorer to launch shortcut")
            import subprocess
            subprocess.Popen(["explorer", file_path])
            return
        except Exception as e:
            print(f"DEBUG [open_file_safely]: explorer launch failed: {e}")

    try:
        print(f"DEBUG [open_file_safely]: Calling os.startfile('{file_path}')")
        os.startfile(file_path)
        print(f"DEBUG [open_file_safely]: os.startfile succeeded.")
    except Exception as e:
        print(f"DEBUG [open_file_safely]: os.startfile failed with exception: {e}")
        # Ultimate fallback: simulate Windows shell execution exactly using explorer
        try:
            print(f"DEBUG [open_file_safely]: Fallback -> Calling explorer")
            import subprocess
            subprocess.Popen(["explorer", file_path])
            print(f"DEBUG [open_file_safely]: explorer succeeded.")
        except Exception as e2:
            print(f"DEBUG [open_file_safely]: explorer failed with exception: {e2}")


import ctypes
import time
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class DesktopDoubleClickListener(QObject):
    double_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._check_click)
        self._was_down = False
        self._last_click_time = 0
        self._last_click_pos = (0, 0)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def _check_click(self):
        try:
            state = win32api.GetAsyncKeyState(0x01)
            is_down = bool(state & 0x8000)

            if is_down and not self._was_down:
                now = time.time()
                pos = win32gui.GetCursorPos()

                double_click_time = win32gui.GetDoubleClickTime() / 1000.0
                dt = now - self._last_click_time
                dx = abs(pos[0] - self._last_click_pos[0])
                dy = abs(pos[1] - self._last_click_pos[1])

                self._last_click_time = now
                self._last_click_pos = pos

                if dt <= double_click_time and dx <= 6 and dy <= 6:
                    hwnd = win32gui.WindowFromPoint(pos)
                    if hwnd:
                        cls_name = win32gui.GetClassName(hwnd)
                        if cls_name in ("SysListView32", "Progman", "WorkerW"):
                            self.double_clicked.emit()

            self._was_down = is_down
        except Exception:
            pass


