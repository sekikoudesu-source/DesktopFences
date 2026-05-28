import win32gui
import win32api
import win32con
import commctrl

# Find Desktop SysListView32
hwnd = win32gui.FindWindow("Progman", "Program Manager")
hwnd = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
hwnd = win32gui.FindWindowEx(hwnd, 0, "SysListView32", "FolderView")

if hwnd == 0:
    # WorkerW fallback
    def enum_windows_proc(h, lParam):
        p = win32gui.FindWindowEx(h, 0, "SHELLDLL_DefView", None)
        if p:
            v = win32gui.FindWindowEx(p, 0, "SysListView32", "FolderView")
            if v:
                hwnd_list.append(v)
        return True
    
    hwnd_list = []
    win32gui.EnumWindows(enum_windows_proc, 0)
    if hwnd_list:
        hwnd = hwnd_list[0]

print("Desktop SysListView32 HWND:", hwnd)

if hwnd:
    item_count = win32api.SendMessage(hwnd, commctrl.LVM_GETITEMCOUNT, 0, 0)
    print("Total items:", item_count)
    
    # Try to move item 0 (if exists)
    if item_count > 0:
        item_index = 0
        x, y = 300, 300
        lparam = (y << 16) | (x & 0xFFFF)
        result = win32api.SendMessage(hwnd, commctrl.LVM_SETITEMPOSITION, item_index, lparam)
        print("Move item 0 result:", result)
