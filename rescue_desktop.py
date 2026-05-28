import os
import json
import shutil

import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def rescue():
    RESTORE_MAP_FILE = os.path.join(BASE_DIR, "restore_map.json")
    if not os.path.exists(RESTORE_MAP_FILE):
        print("没有发现映射文件，无需恢复。")
        input("按回车退出...")
        return
        
    with open(RESTORE_MAP_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        
    if not mapping:
        print("映射表为空，无需恢复。")
        input("按回车退出...")
        return
        
    print(f"正在准备将 {len(mapping)} 个文件恢复到桌面原位...")
    restored = 0
    failed = 0
    
    for v_path, orig_path in list(mapping.items()):
        if os.path.exists(v_path):
            os.makedirs(os.path.dirname(orig_path), exist_ok=True)
            try:
                shutil.move(v_path, orig_path)
                restored += 1
                print(f"成功恢复: {orig_path}")
                del mapping[v_path]
            except Exception as e:
                failed += 1
                print(f"失败: {orig_path} ({e})")
        else:
            # 文件在虚拟盒子里已经找不到了，说明用户手动删除了它，直接从记录中移除
            del mapping[v_path]
                
    with open(RESTORE_MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=4)
        
    print(f"\n恢复结束！成功: {restored}，失败: {failed}")
    input("按回车退出...")

if __name__ == '__main__':
    rescue()
