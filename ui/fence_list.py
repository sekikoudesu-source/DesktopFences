import os
import shutil
import subprocess
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView, QMenu, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt, QSize, QFileInfo, QMimeData, QUrl
from PyQt6.QtGui import QAction, QDrag, QIcon

from core.config import save_restore_map

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
        self.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: white;
            }
            QListWidget::item {
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background: rgba(255, 255, 255, 60);
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 30);
            }
        """)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

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
        open_action.triggered.connect(lambda: os.startfile(os.path.join(self.folder_path, item.toolTip())))
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
                os.rename(old_path, new_path)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重命名失败:\n{e}")

    def delete_item(self, item):
        file_path = os.path.join(self.folder_path, item.toolTip())
        reply = QMessageBox.question(self, "确认删除", f"确定要永久删除文件 {item.toolTip()} 吗？\n(此操作将直接删除文件)", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(file_path)
                manager = self.parent().manager
                if file_path in manager.restore_map:
                    del manager.restore_map[file_path]
                    save_restore_map(manager.restore_map)
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
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path) or os.path.isdir(file_path):
                if os.path.dirname(os.path.normpath(file_path)) == os.path.normpath(self.folder_path):
                    continue
                try:
                    dest_path = os.path.join(self.folder_path, os.path.basename(file_path))
                    base, ext = os.path.splitext(os.path.basename(file_path))
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(self.folder_path, f"{base}_{counter}{ext}")
                        counter += 1
                        
                    shutil.move(file_path, dest_path)
                    
                    manager = self.parent().manager
                    manager.restore_map[dest_path] = file_path
                    save_restore_map(manager.restore_map)
                except Exception as e:
                    print(f"Failed to move {file_path}: {e}")
        event.acceptProposedAction()
