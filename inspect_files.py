import json, os

config = json.load(open(r'd:\PythonProject\desktop_fences\dist\config.json', encoding='utf-8'))
rmap = json.load(open(r'd:\PythonProject\desktop_fences\dist\restore_map.json', encoding='utf-8'))

with open("inspect_out.txt", "w", encoding="utf-8") as f:
    for fence in config['fences']:
        f.write(f"\n--- {fence['title']} ---\n")
        fid = fence['id']
        for k, v in rmap.items():
            if fid in k:
                f.write(f"  {os.path.basename(v)}\n")
