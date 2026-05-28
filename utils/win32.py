import win32gui
import win32con

def set_window_bottom(hwnd):
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    )
