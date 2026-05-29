import sys
import os
import uuid
from PyQt6.QtWidgets import QApplication

from core.config import save_config
from ui.manager import FenceManager

if __name__ == '__main__':
    # In Qt6, to stop the Per-Monitor V2 DPI infinite resize loop (when a widget straddles
    # two monitors with different DPIs, causing it to bounce back and forth), we MUST force
    # Qt's Windows platform plugin to use System DPI Awareness (1) instead of Per-Monitor V2 (2).
    # This prevents the physical QSize from jumping when crossing screens!
    import os
    os.environ["QT_QPA_PLATFORM"] = "windows:dpiawareness=1"
    
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
