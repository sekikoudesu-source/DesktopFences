import os
import shutil
import subprocess
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView, QMenu, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt, QSize, QFileInfo, QMimeData, QUrl, QTimer
from PyQt6.QtGui import QAction, QDrag, QIcon, QBrush, QColor
import random

from core.config import save_restore_map, save_config
from utils.win32 import robust_move, open_file_safely

import time
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
from PyQt6.QtGui import QPainter

class NeonTextDelegate(QStyledItemDelegate):
    def __init__(self, list_widget):
        super().__init__(list_widget)
        self.list_widget = list_widget

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        if getattr(self.list_widget, 'current_theme', '') == "cyberpunk":
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if not text: return
            
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            style = option.widget.style()
            item_rect = option.rect
            from PyQt6.QtCore import QRect
            # Icon is 48x48 near top. Place text in the bottom section (height 95 - 52 = 43)
            text_rect = QRect(item_rect.left(), item_rect.top() + 54, item_rect.width(), item_rect.height() - 54)
            
            period_pixels = 80
            offset_x = (time.time() * 30) % period_pixels
            
            from PyQt6.QtGui import QLinearGradient, QPen
            grad = QLinearGradient(text_rect.left() - offset_x, 0, text_rect.left() - offset_x + period_pixels, 0)
            grad.setSpread(QLinearGradient.Spread.RepeatSpread)
            
            grad.setColorAt(0.0, QColor("#ff00ff"))   # Magenta
            grad.setColorAt(0.2, QColor("#00e5ff"))   # Cyan
            grad.setColorAt(0.4, QColor("#39ff14"))   # Neon Green
            grad.setColorAt(0.6, QColor("#ff0055"))   # Neon Pink
            grad.setColorAt(0.8, QColor("#fcee0a"))   # Yellow
            grad.setColorAt(1.0, QColor("#ff00ff"))   # Magenta
            
            painter.setPen(QPen(QBrush(grad), 1))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, text)
            
            painter.restore()

class FenceListWidget(QListWidget):
    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(48, 48))
        self.setGridSize(QSize(85, 95))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setWordWrap(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        self.setItemDelegate(NeonTextDelegate(self))
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.viewport().update)
        
        self.current_theme = "default"
        
        self.apply_theme("default")

    def apply_theme(self, theme="default"):
        color = "#ffffff"
        selected_bg = "rgba(255, 255, 255, 0.25)"
        hover_bg = "rgba(255, 255, 255, 0.14)"
        hover_border = "1px solid rgba(255, 255, 255, 0.35)"
        radius = "8px"

        self.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {color};
                padding: 4px;
            }}
            QListWidget::item {{
                border-radius: {radius};
                padding: 4px;
                border: 1px solid transparent;
            }}
            QListWidget::item:selected {{
                background: {selected_bg};
                border: {hover_border};
            }}
            QListWidget::item:hover {{
                background: {hover_bg};
                border: {hover_border};
            }}
        """)
        self.current_theme = "default"



    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item: return
            
        parent_widget = self.parent()
        if hasattr(parent_widget, '_is_menu_open'):
            parent_widget._is_menu_open = True
            
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2c2c2c; color: white; border: 1px solid #555; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background-color: #0078d7; }
        """)
        
        open_action = QAction("打开 (Open)", self)
        open_action.triggered.connect(lambda: open_file_safely(os.path.join(self.folder_path, item.toolTip())))
        menu.addAction(open_action)
        
        show_action = QAction("在文件夹中显示 (Show in Explorer)", self)
        show_action.triggered.connect(lambda: subprocess.run(['explorer', '/select,', os.path.normpath(os.path.join(self.folder_path, item.toolTip()))]))
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        ren_action = QAction("重命名 (Rename)", self)
        ren_action.triggered.connect(lambda: self.rename_item(item))
        menu.addAction(ren_action)
        
        del_action = QAction("删除 (Delete)", self)
        del_action.triggered.connect(lambda: self.delete_item(item))
        menu.addAction(del_action)
        
        menu.exec(self.mapToGlobal(pos))
        
        if hasattr(parent_widget, '_is_menu_open'):
            parent_widget._is_menu_open = False
            if not parent_widget.underMouse():
                if hasattr(parent_widget, 'check_auto_hide'):
                    parent_widget.check_auto_hide()
        
    def rename_item(self, item):
        old_name = item.toolTip()
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新文件名:", text=old_name)
        if ok and new_name and new_name != old_name:
            old_path = os.path.join(self.folder_path, old_name)
            new_path = os.path.join(self.folder_path, new_name)
            try:
                if os.path.isdir(old_path):
                    shutil.move(old_path, new_path)
                else:
                    os.rename(old_path, new_path)
                
                parent_widget = self.parent()
                if getattr(parent_widget, "is_virtual", False):
                    manager = parent_widget.manager
                    fence_config = next((fc for fc in manager.config["fences"] if fc["id"] == parent_widget.fence_id), None)
                    if fence_config and "files" in fence_config:
                        if old_name in fence_config["files"]:
                            idx = fence_config["files"].index(old_name)
                            fence_config["files"][idx] = new_name
                        save_config(manager.config)
                    parent_widget.load_files()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重命名失败:\n{e}")

    def delete_item(self, item):
        filename = item.toolTip()
        file_path = os.path.join(self.folder_path, filename)
        is_dir = os.path.isdir(file_path)
        type_str = "文件夹" if is_dir else "文件"
        
        reply = QMessageBox.question(self, "确认删除", f"确定要永久删除{type_str} {filename} 吗？\n(此操作将直接删除该{type_str})", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if is_dir:
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                
                parent_widget = self.parent()
                if getattr(parent_widget, "is_virtual", False):
                    manager = parent_widget.manager
                    fence_config = next((fc for fc in manager.config["fences"] if fc["id"] == parent_widget.fence_id), None)
                    if fence_config and "files" in fence_config:
                        if filename in fence_config["files"]:
                            fence_config["files"].remove(filename)
                        save_config(manager.config)
                    parent_widget.load_files()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败:\n{e}")

    def startDrag(self, supportedActions):
        items = self.selectedItems()
        if not items: return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        
        urls = []
        for item in items:
            file_path = os.path.join(self.folder_path, item.toolTip())
            urls.append(QUrl.fromLocalFile(file_path))
            
        mime_data.setUrls(urls)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def dropEvent(self, event):
        parent_widget = self.parent()
        manager = parent_widget.manager
        target_is_virtual = getattr(parent_widget, "is_virtual", False)
        target_fence_id = parent_widget.fence_id
        
        move_tasks = []
        config_changed = False
        
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if not (os.path.isfile(file_path) or os.path.isdir(file_path)):
                continue
                
            filename = os.path.basename(file_path)
            
            # Check if this file is currently in a virtual fence
            source_fence = None
            for fc in manager.config.get("fences", []):
                if fc.get("is_virtual") and filename in fc.get("files", []):
                    source_fence = fc
                    break
                    
            if target_is_virtual:
                # Target is Virtual Fence
                if source_fence:
                    # Source is Virtual, Target is Virtual: Pure virtual transfer!
                    if source_fence["id"] != target_fence_id:
                        if filename in source_fence["files"]:
                            source_fence["files"].remove(filename)
                        
                        # Find target config
                        target_config = next((fc for fc in manager.config["fences"] if fc["id"] == target_fence_id), None)
                        if target_config:
                            if "files" not in target_config:
                                target_config["files"] = []
                            if filename not in target_config["files"]:
                                target_config["files"].append(filename)
                        config_changed = True
                else:
                    # Source is Portal or External: Must physically move to Desktop directory
                    dest_path = os.path.join(self.folder_path, filename)
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(self.folder_path, f"{base}_{counter}{ext}")
                        counter += 1
                    move_tasks.append((file_path, dest_path))
            else:
                # Target is Portal Fence
                if os.path.dirname(os.path.normpath(file_path)) == os.path.normpath(self.folder_path):
                    continue
                dest_path = os.path.join(self.folder_path, filename)
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(self.folder_path, f"{base}_{counter}{ext}")
                    counter += 1
                move_tasks.append((file_path, dest_path))

        # Save config if virtual-to-virtual transfers occurred
        if config_changed:
            save_config(manager.config)
            # Reload all virtual fences
            for f in manager.fences:
                if getattr(f, "is_virtual", False):
                    f.load_files()

        # Handle physical moves asynchronously
        if move_tasks:
            from core.worker import MoveWorker
            self.drop_worker = MoveWorker(move_tasks, parent=self)
            self.drop_worker.finished_move.connect(
                lambda success_map, failed_list: self._on_drop_finished(success_map, failed_list, target_is_virtual, target_fence_id)
            )
            self.drop_worker.start()
            
        # Trigger blackhole effect!
        if hasattr(parent_widget, 'emit_blackhole'):
            parent_widget.emit_blackhole(event.position().toPoint())
            
        event.acceptProposedAction()

    def _on_drop_finished(self, success_map, failed_list, target_is_virtual, target_fence_id):
        if not success_map:
            return
            
        parent_widget = self.parent()
        manager = parent_widget.manager
        config_changed = False
        
        for dest_path, orig_path in success_map.items():
            dest_name = os.path.basename(dest_path)
            orig_name = os.path.basename(orig_path)
            
            # Clean up from any source virtual fence
            for fc in manager.config.get("fences", []):
                if fc.get("is_virtual") and orig_name in fc.get("files", []):
                    fc["files"].remove(orig_name)
                    config_changed = True
            
            # Register in target virtual fence
            if target_is_virtual:
                target_config = next((fc for fc in manager.config["fences"] if fc["id"] == target_fence_id), None)
                if target_config:
                    if "files" not in target_config:
                        target_config["files"] = []
                    if dest_name not in target_config["files"]:
                        target_config["files"].append(dest_name)
                        config_changed = True
                        
        if config_changed:
            save_config(manager.config)
            
        # Reload virtual fences
        for f in manager.fences:
            if getattr(f, "is_virtual", False):
                f.load_files()
