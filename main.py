import sys
import os
import uuid
import traceback
from PyQt6.QtWidgets import QApplication

def crash_handler(exctype, value, tb):
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("=== CRASH TRACEBACK ===", file=sys.stderr)
    print(err_msg, file=sys.stderr)
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(err_msg)
    except Exception:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = crash_handler

from core.config import save_config
from ui.manager import FenceManager

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    manager = FenceManager(app)
    
    if not manager.config["fences"]:
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        
        doc_path = os.path.join(desktop_dir, "Documents")
        if os.path.exists(doc_path):
            fc1 = {"id": str(uuid.uuid4()), "title": "📄 Documents", "path": doc_path, "x": 100, "y": 100, "width": 320, "height": 400}
            manager.config["fences"].append(fc1)
            manager._spawn_fence_widget(fc1)
            
        img_path = os.path.join(desktop_dir, "Images")
        if os.path.exists(img_path):
            fc2 = {"id": str(uuid.uuid4()), "title": "🖼️ Images", "path": img_path, "x": 450, "y": 100, "width": 320, "height": 400}
            manager.config["fences"].append(fc2)
            manager._spawn_fence_widget(fc2)
            
        save_config(manager.config)

    sys.exit(app.exec())
