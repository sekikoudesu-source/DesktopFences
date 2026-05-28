import os

def guess_category(filename):
    name, ext = os.path.splitext(filename)
    name = name.lower()
    ext = ext.lower()

    if any(k in name for k in ["steam", "league of legends", "astroneer", "subnautica", "土豆兄弟", "peak", "seergame", "brotato", "bongo", "goose", "nightmares", "ori", "overcooked", "palworld", "riot", "uu", "valorant", "wallpaper", "三国杀", "双人成行", "双影奇境", "无畏契约", "百田", "箭箭剑", "英雄联盟", "超凡双生", "雷神", "饥荒", "wegame", "幻兽帕鲁"]):
        return "🎮 游戏天地"
        
    if any(k in name for k in ["pycharm", "antigravity", "virtualbox", "vscode", "git"]):
        return "💻 极客开发"
        
    if any(k in name for k in ["微信", "qq", "discord", "wechat"]):
        if "音乐" not in name:
            return "💬 社交通讯"
            
    if any(k in name for k in ["zoom", "qq音乐", "netease"]):
        return "🎵 音乐与办公"
        
    if any(k in name for k in ["edge", "clash", "百度网盘", "chrome"]):
        return "🛠️ 实用工具"
        
    # Generic fallbacks
    if ext in [".lnk", ".url", ".exe"]:
        return "🛠️ 实用工具"
        
    if any(k in name for k in ["setup", "install", "v1.", "v2.", "安装"]):
        return "📦 安装包与环境"
    if ext in [".msi", ".iso"]:
        return "📦 安装包与环境"
        
    if any(k in name for k in ["总结", "报告", "简历", "财务", "report", "doc", "文档", "合同", "修考", "课题", "证明书", "愿书"]):
        return "💼 工作与文档"
    if ext in [".doc", ".docx", ".pdf", ".txt", ".rtf", ".ppt", ".pptx", ".md", ".xlsx", ".xls"]:
        return "💼 工作与文档"
        
    if any(k in name for k in ["数据", "统计", "data", "报表"]):
        return "📊 数据与表格"
    if ext in [".csv", ".sql", ".json"]:
        return "📊 数据与表格"
        
    if ext in [".py", ".js", ".html", ".cpp", ".c", ".h", ".java", ".go", ".ts", ".css", ".php"]:
        return "💻 极客开发"
        
    if ext in [".psd", ".ai", ".svg", ".mp4", ".mp3", ".jpg", ".jpeg", ".png", ".gif", ".mov", ".wav", ".cad", ".blend"]:
        return "🎨 设计与多媒体"
        
    if ext in [".zip", ".rar", ".7z", ".tar", ".gz"]:
        return "🗜️ 压缩包"
        
    return "🧩 杂项"
