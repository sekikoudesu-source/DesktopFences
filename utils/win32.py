import win32gui
import win32con
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


def set_window_bottom(hwnd):
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    )


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
