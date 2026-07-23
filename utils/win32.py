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
