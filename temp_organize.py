import os
import shutil
import json
import uuid

# Paths
USER_DESKTOP = r"C:\Users\28594\Desktop"
PUBLIC_DESKTOP = r"C:\Users\Public\Desktop"
DATA_DIR = r"D:\PythonProject\desktop_fences\dist\data"
CONFIG_FILE = r"D:\PythonProject\desktop_fences\dist\config.json"
RESTORE_MAP_FILE = r"D:\PythonProject\desktop_fences\dist\restore_map.json"

# (Rescue step skipped)

# Remove empty dirs in data
for d in os.listdir(DATA_DIR):
    d_path = os.path.join(DATA_DIR, d)
    if os.path.isdir(d_path):
        try:
            shutil.rmtree(d_path)
        except:
            pass

# 2. Define New Categories and Fences
categories = {
    "🎮 游戏天地": [
        "Steam", "League of Legends", "ASTRONEER", "Subnautica", "土豆兄弟", "PEAK", "SeerGame"
    ],
    "💻 极客开发": [
        "PyCharm", "Antigravity", "VirtualBox"
    ],
    "💬 社交通讯": [
        "QQ", "微信", "Discord"
    ],
    "🛠️ 实用工具": [
        "Edge", "Clash", "百度网盘"
    ],
    "🎵 音乐与办公": [
        "QQ音乐", "Zoom", "钢琴谱"
    ]
}

# Generate UUIDs and configs for fences
fences_config = []
cat_to_uuid = {}

positions = [
    (100, 100), (450, 100), (800, 100),
    (100, 550), (450, 550)
]

for i, (cat_name, keywords) in enumerate(categories.items()):
    fid = str(uuid.uuid4())
    cat_to_uuid[cat_name] = fid
    fences_config.append({
        "id": fid,
        "title": cat_name,
        "path": os.path.join(DATA_DIR, fid),
        "x": positions[i][0],
        "y": positions[i][1],
        "width": 320,
        "height": 400
    })
    os.makedirs(os.path.join(DATA_DIR, fid), exist_ok=True)

# 3. Create mapping
restore_map = {}

def categorize(filename):
    for cat_name, keywords in categories.items():
        for kw in keywords:
            if kw.lower() in filename.lower():
                return cat_name
    return "🛠️ 实用工具" # Default fallback

def scan_desktop(desktop_path):
    if not os.path.exists(desktop_path): return
    for f in os.listdir(desktop_path):
        if f.lower().startswith("desktop.ini"): continue
        full_path = os.path.join(desktop_path, f)
        if os.path.isfile(full_path):
            cat_name = categorize(f)
            fid = cat_to_uuid[cat_name]
            v_path = os.path.join(DATA_DIR, fid, f)
            restore_map[v_path] = full_path

scan_desktop(USER_DESKTOP)
scan_desktop(PUBLIC_DESKTOP)

# 4. Save to files
with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
    json.dump({"opacity": 150, "fences": fences_config}, f, indent=4)

with open(RESTORE_MAP_FILE, 'w', encoding='utf-8') as f:
    json.dump(restore_map, f, indent=4)

print("AI Categorization complete!")
