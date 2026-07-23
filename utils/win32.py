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
        attach_to_desktop(hwnd)
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
import ctypes.wintypes
import time
from PyQt6.QtCore import QThread, pyqtSignal

class DesktopDoubleCheckThread(QThread):
    double_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.hook = None
        self._last_click_time = 0
        self._last_click_pos = (0, 0)
        self._hook_proc = None

    def run(self):
        self.running = True

        CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("pt", POINT),
                ("mouseData", ctypes.wintypes.DWORD),
                ("flags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
            ]

        user32 = ctypes.windll.user32
        WH_MOUSE_LL = 14
        WM_LBUTTONDOWN = 0x0201
        double_click_time = user32.GetDoubleClickTime() / 1000.0

        def hook_callback(nCode, wParam, lParam):
            if nCode >= 0 and wParam == WM_LBUTTONDOWN:
                try:
                    ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    now = time.time()
                    pos = (ms.pt.x, ms.pt.y)
                    
                    dt = now - self._last_click_time
                    dx = abs(pos[0] - self._last_click_pos[0])
                    dy = abs(pos[1] - self._last_click_pos[1])
                    
                    self._last_click_time = now
                    self._last_click_pos = pos

                    if dt <= double_click_time and dx <= 5 and dy <= 5:
                        hwnd = user32.WindowFromPoint(ms.pt)
                        if hwnd:
                            buf = ctypes.create_unicode_buffer(256)
                            user32.GetClassNameW(hwnd, buf, 256)
                            cls_name = buf.value
                            
                            if cls_name in ("SysListView32", "Progman", "WorkerW"):
                                self.double_clicked.emit()
                except Exception:
                    pass
            return user32.CallNextHookEx(self.hook, nCode, wParam, lParam)

        self._hook_proc = CMPFUNC(hook_callback)
        self.hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._hook_proc, None, 0)
        
        msg = ctypes.wintypes.MSG()
        while self.running:
            bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if bRet == 0 or bRet == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self.hook:
            user32.UnhookWindowsHookEx(self.hook)
            self.hook = None

    def stop(self):
        self.running = False
        user32 = ctypes.windll.user32
        user32.PostQuitMessage(0)

