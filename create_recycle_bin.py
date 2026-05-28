import json
import os
import win32com.client

config_path = r'd:\PythonProject\desktop_fences\dist\config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

util_path = None
for fence in config['fences']:
    if '实用工具' in fence['title']:
        util_path = fence['path']
        break

if util_path:
    lnk_path = os.path.join(util_path, "回收站.lnk")
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_path)
    shortcut.Targetpath = "explorer.exe"
    shortcut.Arguments = "shell:RecycleBinFolder"
    shortcut.IconLocation = "imageres.dll,54" # Windows 10/11 standard Recycle Bin icon
    shortcut.save()
    print("Created recycle bin shortcut at:", lnk_path)
