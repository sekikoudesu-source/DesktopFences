import os
import sys
import shutil
import uuid
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QFileDialog, QInputDialog, QMessageBox
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt

from core.config import load_config, save_config, load_restore_map, save_restore_map, DATA_DIR, BASE_DIR
from core.categorization import guess_category
from ui.fence_widget import FenceWidget
from ui.settings import SettingsDialog
from utils.win32 import set_window_bottom

class FenceManager:
    def __init__(self, app):
        self.app = app
        self.config = load_config()
        self.fences = []
        self.restore_map = load_restore_map()
        
        self.app.aboutToQuit.connect(self.on_quit)
        
        self.tray_icon = QSystemTrayIcon(self.app)
        from PyQt6.QtWidgets import QStyle
        icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
        self.tray_icon.setIcon(icon)
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
        
        self.restore_fences_on_startup()
        self.load_all_fences()

    def restore_fences_on_startup(self):
        for v_path, orig_path in list(self.restore_map.items()):
            if os.path.exists(orig_path):
                os.makedirs(os.path.dirname(v_path), exist_ok=True)
                try:
                    shutil.move(orig_path, v_path)
                except Exception:
                    pass
            elif not os.path.exists(v_path):
                del self.restore_map[v_path]
        save_restore_map(self.restore_map)

    def update_opacity(self, opacity):
        self.config["opacity"] = opacity
        for fence in self.fences:
            fence.update()
        save_config(self.config)
        
    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
        
    def on_quit(self):
        for v_path, orig_path in list(self.restore_map.items()):
            if os.path.exists(v_path):
                os.makedirs(os.path.dirname(orig_path), exist_ok=True)
                try:
                    shutil.move(v_path, orig_path)
                except Exception as e:
                    pass
            else:
                del self.restore_map[v_path]
                
        save_restore_map(self.restore_map)
        
    def auto_organize_desktop(self):
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        public_desktop_dir = r"C:\Users\Public\Desktop"
        
        mapped_paths = [os.path.normpath(fc["path"]) for fc in self.config["fences"]]
        
        files_to_move = []
        folders_to_check_empty = set()
        
        def scan_dir(d):
            for root, dirs, files in os.walk(d):
                if os.path.normpath(root) == os.path.normpath(d):
                    pass
                else:
                    if os.path.normpath(root) in mapped_paths:
                        continue
                    folders_to_check_empty.add(root)
                    
                for f in files:
                    if f.lower() == "desktop.ini":
                        continue
                    path = os.path.join(root, f)
                    if os.path.normpath(path) in mapped_paths:
                        continue
                    files_to_move.append((f, path))
                    
        if os.path.exists(desktop_dir): scan_dir(desktop_dir)
        if os.path.exists(public_desktop_dir): scan_dir(public_desktop_dir)
                
        if not files_to_move:
            QMessageBox.information(None, "提示", "桌面上已经没有可整理的散落文件或文件夹了！")
            return
            
        categorized = {}
        failed_moves = []
        for f, path in files_to_move:
            cat = guess_category(f)
            categorized.setdefault(cat, []).append((f, path))
            
        for cat_name, items in categorized.items():
            fence_config = next((fc for fc in self.config["fences"] if fc["title"] == cat_name), None)
            
            if not fence_config:
                fence_id = str(uuid.uuid4())
                folder_path = os.path.join(DATA_DIR, fence_id)
                os.makedirs(folder_path, exist_ok=True)
                
                count = len(self.fences)
                x = 50 + (count % 4) * 350
                y = 50 + (count // 4) * 450
                
                fence_config = {
                    "id": fence_id,
                    "title": cat_name,
                    "path": folder_path,
                    "x": x,
                    "y": y,
                    "width": 320,
                    "height": 400
                }
                self.config["fences"].append(fence_config)
                self._spawn_fence_widget(fence_config)
            
            dest_dir = fence_config["path"]
            for f, orig_path in items:
                dest_path = os.path.join(dest_dir, f)
                base, ext = os.path.splitext(f)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                    counter += 1
                    
                try:
                    shutil.move(orig_path, dest_path)
                    self.restore_map[dest_path] = orig_path
                except Exception as e:
                    failed_moves.append(orig_path)
                    
        save_restore_map(self.restore_map)
        save_config(self.config)
        
        for folder in sorted(list(folders_to_check_empty), key=len, reverse=True):
            try:
                if not os.listdir(folder):
                    os.rmdir(folder)
            except:
                pass
        
        if failed_moves:
            msg = f"🎉 整理完成，但有 {len(failed_moves)} 个系统权限文件未能移动。\n\n解决办法：请关闭程序后，以【管理员身份】运行代码或终端即可。"
            QMessageBox.warning(None, "部分完成", msg)
        else:
            QMessageBox.information(None, "完成", "🎉 桌面一键深度拆解整理完成！关闭程序时将自动还原。")

    def load_all_fences(self):
        for fc in self.config["fences"]:
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
            folder_path = os.path.join(DATA_DIR, fence_id)
            os.makedirs(folder_path, exist_ok=True)
            
            fc = {
                "id": fence_id,
                "title": f"📦 {title}",
                "path": folder_path,
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
                "x": 350,
                "y": 350,
                "width": 320,
                "height": 400
            }
            self.config["fences"].append(fc)
            save_config(self.config)
            self._spawn_fence_widget(fc)
