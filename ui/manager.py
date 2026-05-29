import os
import sys
import shutil
import uuid
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QFileDialog, QInputDialog, QMessageBox
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher

from core.config import load_config, save_config, load_restore_map, save_restore_map, DATA_DIR, BASE_DIR, RES_DIR, get_desktop_dir
from core.categorization import guess_category
from core.worker import MoveWorker
from ui.fence_widget import FenceWidget
from ui.settings import SettingsDialog
from utils.win32 import set_window_bottom, robust_move, set_desktop_icons_visible

class FenceManager:
    def __init__(self, app):
        self.app = app
        self.desktop_dir = get_desktop_dir()
        self.config = load_config()
        self.fences = []
        self.restore_map = load_restore_map()
        
        # Check if we need to migrate from old physical move strategy
        self.migrate_old_physical_strategy()
        
        # Setup Desktop File Watcher
        self.desktop_watcher = QFileSystemWatcher([self.desktop_dir], self.app)
        self.reconcile_timer = QTimer(self.app)
        self.reconcile_timer.setSingleShot(True)
        self.reconcile_timer.timeout.connect(self.reconcile_desktop_files)
        self.desktop_watcher.directoryChanged.connect(lambda: self.reconcile_timer.start(200))
        
        # Perform initial sync
        self.reconcile_desktop_files()
        
        # Apply Hide Desktop Icons setting if active
        if self.config.get("hide_desktop_icons", False):
            set_desktop_icons_visible(False)
            
        # Setup bottom alignment timer to keep fences below other windows on boot / Win+D
        self.bottom_timer = QTimer(self.app)
        self.bottom_timer.setInterval(2000)
        self.bottom_timer.timeout.connect(self.keep_fences_at_bottom)
        self.bottom_timer.start()
        
        self.app.aboutToQuit.connect(self.on_quit)
        
        self.tray_icon = QSystemTrayIcon(self.app)
        icon_path = os.path.join(RES_DIR, "app_icon.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            from PyQt6.QtWidgets import QStyle
            self.tray_icon.setIcon(self.app.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        self.tray_icon.setToolTip("Fences V7 管理器")
        
        menu = QMenu()
        
        auto_action = QAction("✨ 一键智能整理桌面", menu)
        auto_action.triggered.connect(self.auto_organize_desktop)
        menu.addAction(auto_action)
        
        self.startup_action = QAction("🚀 开机自动启动", menu)
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.is_startup_enabled())
        self.startup_action.triggered.connect(self.toggle_startup)
        menu.addAction(self.startup_action)
        
        self.hide_icons_action = QAction("🕶️ 隐藏原生桌面图标", menu)
        self.hide_icons_action.setCheckable(True)
        self.hide_icons_action.setChecked(self.config.get("hide_desktop_icons", False))
        self.hide_icons_action.triggered.connect(self.toggle_hide_desktop_icons)
        menu.addAction(self.hide_icons_action)
        
        menu.addSeparator()
        
        new_virt_action = QAction("新建隐式收纳盒 (Virtual)", menu)
        new_virt_action.triggered.connect(self.create_virtual_fence)
        menu.addAction(new_virt_action)
        
        new_map_action = QAction("新建文件夹映射 (Portal)", menu)
        new_map_action.triggered.connect(self.create_mapped_fence)
        menu.addAction(new_map_action)
        
        menu.addSeparator()
        
        settings_action = QAction("设置面板 (Settings)", menu)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        exit_action = QAction("退出程序 (Exit)", menu)
        exit_action.triggered.connect(self.app.quit)
        menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        
        self.load_all_fences()

    def change_global_theme(self, theme):
        self.config["theme"] = theme
        save_config(self.config)
        for fence in self.fences:
            fence.apply_theme()

    def migrate_old_physical_strategy(self):
        config_changed = False
        for fc in self.config.get("fences", []):
            path_str = os.path.normpath(fc.get("path", ""))
            data_dir_str = os.path.normpath(DATA_DIR)
            
            # If the path is inside DATA_DIR, force it to be a virtual fence
            if path_str.startswith(data_dir_str) or fc.get("path") == "virtual":
                if not fc.get("is_virtual", False) or fc.get("path") != "virtual":
                    fc["is_virtual"] = True
                    fc["path"] = "virtual"
                    config_changed = True
                    
            if fc.get("is_virtual") and "files" not in fc:
                fc["files"] = []
                config_changed = True

        if self.restore_map:
            print("发现旧版本的物理整理映射表，正在进行迁移恢复...")
            for v_path, orig_path in list(self.restore_map.items()):
                filename = os.path.basename(orig_path)
                parent_dir = os.path.dirname(v_path)
                fence_id = os.path.basename(parent_dir)
                
                # Find the fence config
                fence_config = next((fc for fc in self.config.get("fences", []) if fc["id"] == fence_id), None)
                
                # If the file is currently in DATA_DIR, move it back to desktop (orig_path)
                if os.path.exists(v_path):
                    try:
                        os.makedirs(os.path.dirname(orig_path), exist_ok=True)
                        robust_move(v_path, orig_path)
                    except Exception as e:
                        print(f"迁移恢复文件失败: {v_path} -> {orig_path}, 错误: {e}")
                
                # Associate the file with the virtual fence
                if fence_config and fence_config.get("is_virtual"):
                    if filename not in fence_config["files"]:
                        fence_config["files"].append(filename)
                        config_changed = True
            
            # Clear restore map since all files are now migrated back to desktop
            self.restore_map = {}
            save_restore_map(self.restore_map)
            config_changed = True
            
            # Try to clean up DATA_DIR
            try:
                if os.path.exists(DATA_DIR):
                    shutil.rmtree(DATA_DIR)
            except Exception as e:
                print(f"清理临时目录失败: {e}")
                
        if config_changed:
            save_config(self.config)

    def reconcile_desktop_files(self):
        if not os.path.exists(self.desktop_dir):
            return
            
        desktop_files = []
        try:
            for entry in os.scandir(self.desktop_dir):
                name = entry.name
                if name.lower() == "desktop.ini":
                    continue
                if name.startswith("~$"):
                    continue
                desktop_files.append(name)
        except Exception as e:
            print(f"扫描桌面文件失败: {e}")
            return

        registered_files = set()
        unclassified_fence = None
        config_changed = False
        
        # Reconcile files in virtual fences
        for fc in self.config.get("fences", []):
            if fc.get("is_virtual"):
                if "files" not in fc:
                    fc["files"] = []
                    config_changed = True
                
                # Filter out files that no longer exist on the desktop
                old_len = len(fc["files"])
                fc["files"] = [f for f in fc["files"] if f in desktop_files]
                if len(fc["files"]) != old_len:
                    config_changed = True
                    
                registered_files.update(fc["files"])
                
                if fc.get("id") == "unclassified_fence" or fc.get("title") == "未分类 (Unclassified)":
                    unclassified_fence = fc

        # Find unregistered files on desktop
        unregistered_files = [f for f in desktop_files if f not in registered_files]

        if unregistered_files:
            if not unclassified_fence:
                # Create the default unclassified fence
                unclassified_id = "unclassified_fence"
                unclassified_fence = next((fc for fc in self.config.get("fences", []) if fc["id"] == unclassified_id), None)
                if not unclassified_fence:
                    count = len(self.fences)
                    x = 50 + (count % 4) * 350
                    y = 50 + (count // 4) * 450
                    unclassified_fence = {
                        "id": unclassified_id,
                        "title": "未分类 (Unclassified)",
                        "path": "virtual",
                        "is_virtual": True,
                        "files": [],
                        "x": x,
                        "y": y,
                        "width": 320,
                        "height": 400
                    }
                    self.config["fences"].append(unclassified_fence)
                    self._spawn_fence_widget(unclassified_fence)
                    config_changed = True
            
            # Add unregistered files to unclassified
            for f in unregistered_files:
                if f not in unclassified_fence["files"]:
                    unclassified_fence["files"].append(f)
                    config_changed = True

        if config_changed:
            save_config(self.config)

        # Notify virtual fences to reload their UI
        for fence in self.fences:
            if getattr(fence, "is_virtual", False):
                fence.load_files()

    def update_opacity(self, opacity):
        self.config["opacity"] = opacity
        for fence in self.fences:
            fence.update()
        save_config(self.config)
        
    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
        
    def on_quit(self):
        set_desktop_icons_visible(True)
        save_config(self.config)
        
    def toggle_hide_desktop_icons(self, checked):
        self.config["hide_desktop_icons"] = checked
        save_config(self.config)
        set_desktop_icons_visible(not checked)
        
    def keep_fences_at_bottom(self):
        for fence in self.fences:
            if fence.isVisible():
                try:
                    hwnd = int(fence.winId())
                    set_window_bottom(hwnd)
                except Exception:
                    pass
        
    def auto_organize_desktop(self):
        # 1. Reconcile first to make sure everything is up to date
        self.reconcile_desktop_files()
        
        # 2. Get list of files in the "未分类" fence
        unclassified_fence = next((fc for fc in self.config.get("fences", []) if fc["id"] == "unclassified_fence"), None)
        if not unclassified_fence or not unclassified_fence.get("files"):
            QMessageBox.information(None, "提示", "桌面上没有发现未分类的文件！")
            return
            
        files_to_organize = list(unclassified_fence["files"])
        
        categorized = {}
        for f in files_to_organize:
            cat = guess_category(f)
            categorized.setdefault(cat, []).append(f)
            
        if not categorized:
            return
            
        for cat_name, items in categorized.items():
            # Find or create virtual fence for this category
            fence_config = next((fc for fc in self.config.get("fences", []) if fc["title"] == cat_name), None)
            if not fence_config:
                fence_id = str(uuid.uuid4())
                
                count = len(self.fences)
                x = 50 + (count % 4) * 350
                y = 50 + (count // 4) * 450
                
                fence_config = {
                    "id": fence_id,
                    "title": cat_name,
                    "path": "virtual",
                    "is_virtual": True,
                    "files": [],
                    "x": x,
                    "y": y,
                    "width": 320,
                    "height": 400
                }
                self.config["fences"].append(fence_config)
                self._spawn_fence_widget(fence_config)
            
            # Add items to the target fence and remove from unclassified
            if "files" not in fence_config:
                fence_config["files"] = []
                
            for f in items:
                if f not in fence_config["files"]:
                    fence_config["files"].append(f)
                if f in unclassified_fence["files"]:
                    unclassified_fence["files"].remove(f)
                    
        # Save config
        save_config(self.config)
        
        # Trigger reload of all virtual fences
        for fence in self.fences:
            if getattr(fence, "is_virtual", False):
                fence.load_files()
                
        QMessageBox.information(None, "完成", "🎉 桌面一键深度拆解整理完成！")

    def load_all_fences(self):
        spawned_ids = {f.fence_id for f in self.fences}
        for fc in self.config.get("fences", []):
            if fc["id"] not in spawned_ids:
                self._spawn_fence_widget(fc)
            
    def is_startup_enabled(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "DesktopFences")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def toggle_startup(self, checked):
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if checked:
                if getattr(sys, 'frozen', False):
                    cmd = f'"{sys.executable}"'
                else:
                    python_exe = os.path.join(BASE_DIR, "venv", "Scripts", "pythonw.exe")
                    main_py = os.path.join(BASE_DIR, "main.py")
                    cmd = f'"{python_exe}" "{main_py}"'
                winreg.SetValueEx(key, "DesktopFences", 0, winreg.REG_SZ, cmd)
                QMessageBox.information(None, "设置成功", "已开启开机自启！\n下次开机时，收纳盒将在后台静默自动运行。")
            else:
                winreg.DeleteValue(key, "DesktopFences")
                QMessageBox.information(None, "设置成功", "已关闭开机自启！")
            winreg.CloseKey(key)
        except Exception as e:
            QMessageBox.warning(None, "错误", f"设置开机启动失败:\n{e}")
            self.startup_action.setChecked(not checked)

    def _spawn_fence_widget(self, fc):
        fence = FenceWidget(fc, self)
        fence.show()
        hwnd = int(fence.winId())
        set_window_bottom(hwnd)
        self.fences.append(fence)

    def create_virtual_fence(self):
        title, ok = QInputDialog.getText(None, "虚拟收纳盒", "请输入收纳盒名称:")
        if ok and title:
            fence_id = str(uuid.uuid4())
            fc = {
                "id": fence_id,
                "title": f"📦 {title}",
                "path": "virtual",
                "is_virtual": True,
                "files": [],
                "x": 300,
                "y": 300,
                "width": 320,
                "height": 400
            }
            self.config["fences"].append(fc)
            save_config(self.config)
            self._spawn_fence_widget(fc)

    def create_mapped_fence(self):
        folder = QFileDialog.getExistingDirectory(None, "选择要映射在桌面的文件夹")
        if folder:
            title = "📁 " + os.path.basename(folder)
            fc = {
                "id": str(uuid.uuid4()),
                "title": title,
                "path": folder,
                "is_virtual": False,
                "x": 350,
                "y": 350,
                "width": 320,
                "height": 400
            }
            self.config["fences"].append(fc)
            save_config(self.config)
            self._spawn_fence_widget(fc)
