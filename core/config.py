import os
import sys
import json

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    RES_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RES_DIR = BASE_DIR

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
RESTORE_MAP_FILE = os.path.join(BASE_DIR, "restore_map.json")

def get_desktop_dir():
    if os.name == 'nt':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
            path, _ = winreg.QueryValueEx(key, "Desktop")
            winreg.CloseKey(key)
            return os.path.expandvars(path)
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"opacity": 150, "fences": []}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
        
def load_restore_map():
    if not os.path.exists(RESTORE_MAP_FILE):
        return {}
    with open(RESTORE_MAP_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_restore_map(mapping):
    with open(RESTORE_MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=4)
