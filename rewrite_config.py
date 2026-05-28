import os
import shutil
import json
import uuid
import sys

sys.path.append(r"d:\PythonProject\desktop_fences")
from core.categorization import guess_category

USER_DESKTOP = r"C:\Users\28594\Desktop"
PUBLIC_DESKTOP = r"C:\Users\Public\Desktop"
DATA_DIR = r"D:\PythonProject\desktop_fences\dist\data"
CONFIG_FILE = r"D:\PythonProject\desktop_fences\dist\config.json"
RESTORE_MAP_FILE = r"D:\PythonProject\desktop_fences\dist\restore_map.json"

# 1. Rescue files back to desktop
def rescue_files():
    for root, dirs, files in os.walk(DATA_DIR):
        for f in files:
            src = os.path.join(root, f)
            dst = os.path.join(USER_DESKTOP, f)
            if not os.path.exists(dst):
                try: shutil.move(src, dst)
                except: pass
            else:
                base, ext = os.path.splitext(f)
                counter = 1
                while os.path.exists(dst):
                    dst = os.path.join(USER_DESKTOP, f"{base}_{counter}{ext}")
                    counter += 1
                try: shutil.move(src, dst)
                except: pass

rescue_files()
try: shutil.rmtree(DATA_DIR)
except: pass
os.makedirs(DATA_DIR, exist_ok=True)

# Clean up empty folders on Desktop
for desk in [USER_DESKTOP, PUBLIC_DESKTOP]:
    if os.path.exists(desk):
        for root, dirs, files in os.walk(desk, topdown=False):
            if root != desk:
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                except:
                    pass

# 2. Scan desktops and categorize recursively
files_to_move = []
for desk in [USER_DESKTOP, PUBLIC_DESKTOP]:
    if not os.path.exists(desk): continue
    for root, dirs, files in os.walk(desk):
        for f in files:
            if f.lower() == "desktop.ini": continue
            path = os.path.join(root, f)
            files_to_move.append((f, path))

categorized = {}
for f, path in files_to_move:
    cat = guess_category(f)
    categorized.setdefault(cat, []).append((f, path))

# 3. Build Config and Restore Map dynamically based on matched categories
fences_config = []
restore_map = {}

positions = [
    (100, 100), (450, 100), (800, 100), (1150, 100),
    (100, 550), (450, 550), (800, 550), (1150, 550),
    (100, 1000), (450, 1000), (800, 1000), (1150, 1000)
]

for i, (cat_name, items) in enumerate(categorized.items()):
    fid = str(uuid.uuid4())
    x, y = positions[i % len(positions)]
    
    fences_config.append({
        "id": fid,
        "title": cat_name,
        "path": os.path.join(DATA_DIR, fid),
        "x": x,
        "y": y,
        "width": 320,
        "height": 400
    })
    
    dest_dir = os.path.join(DATA_DIR, fid)
    os.makedirs(dest_dir, exist_ok=True)
    
    for f, orig_path in items:
        v_path = os.path.join(dest_dir, f)
        base, ext = os.path.splitext(f)
        counter = 1
        while v_path in restore_map:
            v_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
            counter += 1
        restore_map[v_path] = orig_path

with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
    json.dump({"opacity": 150, "fences": fences_config}, f, indent=4)

with open(RESTORE_MAP_FILE, 'w', encoding='utf-8') as f:
    json.dump(restore_map, f, indent=4)

print(f"Generated {len(fences_config)} categories with {len(restore_map)} files.")
