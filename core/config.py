import os
import sys
import json

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
RESTORE_MAP_FILE = os.path.join(BASE_DIR, "restore_map.json")

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
