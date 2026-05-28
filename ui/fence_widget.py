import os
import shutil
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QMessageBox, QListWidgetItem, QFileIconProvider
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QFileInfo, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QAction, QIcon

from core.config import DATA_DIR, save_config, save_restore_map
from ui.fence_list import FenceListWidget

ICON_CACHE = {}

def get_icon_for_file(file_path, provider):
    ext = os.path.splitext(file_path)[1].lower()
    
    is_unique = ext in [".exe", ".lnk", ".url"]
    cache_key = file_path if is_unique else ext

    if cache_key in ICON_CACHE:
        return ICON_CACHE[cache_key]

    icon = None
    if ext == ".url":
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith("IconFile="):
                        icon_path = line.strip().split("=", 1)[1]
                        if os.path.exists(icon_path):
                            icon = QIcon(icon_path)
                            break
        except Exception:
            pass
            
    if not icon:
        icon = provider.icon(QFileInfo(file_path))
        
    ICON_CACHE[cache_key] = icon
    return icon

class FenceWidget(QWidget):
    def __init__(self, fence_config, manager):
        super().__init__()
        self.manager = manager
        self.fence_id = fence_config["id"]
        self.title = fence_config["title"]
        self.folder_path = fence_config["path"]
        
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path, exist_ok=True)
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(fence_config.get("x", 100), fence_config.get("y", 100), 
                         fence_config.get("width", 320), fence_config.get("height", 400))
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.label = QLabel(self.title, self)
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 16px; background: transparent;")
        self.label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.label.customContextMenuRequested.connect(self.show_title_context_menu)
        layout.addWidget(self.label)
        
        self.list_widget = FenceListWidget(self.folder_path, self)
        self.list_widget.itemDoubleClicked.connect(self.open_file)
        layout.addWidget(self.list_widget)
        
        self.load_files()
        
        from PyQt6.QtCore import QFileSystemWatcher
        self.watcher = QFileSystemWatcher([self.folder_path])
        self.reload_timer = QTimer(self)
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self.load_files)
        self.watcher.directoryChanged.connect(lambda: self.reload_timer.start(100))

        self._is_tracking = False
        self._start_pos = None
        self._is_resizing = False
        self._resize_edges = ""
        self._resize_start_geometry = None
        self._is_menu_open = False

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.is_collapsed = False
        self.snap_edge = None
        self.expanded_pos = self.pos()

    def show_title_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2c2c2c; color: white; border: 1px solid #555; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background-color: #d73a49; } 
        """)
        del_action = QAction("❌ 解散收纳盒 (Destroy)", self)
        del_action.triggered.connect(self.destroy_fence)
        menu.addAction(del_action)
        menu.exec(self.label.mapToGlobal(pos))
        
    def destroy_fence(self):
        reply = QMessageBox.question(self, "确认解散", f"确定要解散【{self.title}】吗？\n隐式收纳盒内的文件将被退回桌面或原处！", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
            
        is_virtual = os.path.normpath(self.folder_path).startswith(os.path.normpath(DATA_DIR))
        
        if is_virtual:
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            if os.path.exists(self.folder_path):
                for filename in os.listdir(self.folder_path):
                    file_path = os.path.join(self.folder_path, filename)
                    if not os.path.isfile(file_path): continue
                    
                    orig_path = self.manager.restore_map.get(file_path)
                    if orig_path:
                        dest = orig_path
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        del self.manager.restore_map[file_path]
                    else:
                        dest = os.path.join(desktop_dir, filename)
                        
                    base, ext = os.path.splitext(os.path.basename(dest))
                    dest_dir_name = os.path.dirname(dest)
                    counter = 1
                    while os.path.exists(dest):
                        dest = os.path.join(dest_dir_name, f"{base}_{counter}{ext}")
                        counter += 1
                        
                    try:
                        shutil.move(file_path, dest)
                    except:
                        pass
                try:
                    shutil.rmtree(self.folder_path)
                except:
                    pass
                save_restore_map(self.manager.restore_map)
                
        self.manager.config["fences"] = [f for f in self.manager.config["fences"] if f["id"] != self.fence_id]
        save_config(self.manager.config)
        
        if self in self.manager.fences:
            self.manager.fences.remove(self)
        self.close()
        self.deleteLater()

    def load_files(self):
        if not os.path.exists(self.folder_path): return
            
        self.list_widget.clear()
        provider = QFileIconProvider()
        fm = self.list_widget.fontMetrics()
        
        for filename in os.listdir(self.folder_path):
            if filename.lower() == "desktop.ini": continue
                
            file_path = os.path.join(self.folder_path, filename)
            icon = get_icon_for_file(file_path, provider)
            
            display_name = os.path.splitext(filename)[0]
            elided_text = fm.elidedText(display_name, Qt.TextElideMode.ElideMiddle, 75)
            
            item = QListWidgetItem(icon, elided_text)
            item.setToolTip(filename)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_widget.addItem(item)
                
    def open_file(self, item):
        file_path = os.path.join(self.folder_path, item.toolTip())
        if os.path.exists(file_path):
            os.startfile(file_path)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        opacity = self.manager.config.get("opacity", 64)
        painter.setBrush(QColor(0, 0, 0, opacity))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawRoundedRect(self.rect(), 10.0, 10.0)
        
        if self.is_collapsed and getattr(self, 'snap_edge', None):
            painter.setPen(QColor(255, 255, 255, 200))
            font = painter.font()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            
            if self.snap_edge in ('left', 'right'):
                y_pos = 30
                fm = painter.fontMetrics()
                line_height = fm.height()
                for char in self.title:
                    char_width = fm.horizontalAdvance(char)
                    if self.snap_edge == 'left':
                        x_pos = self.width() - 35 + (35 - char_width) // 2
                    else:
                        x_pos = (35 - char_width) // 2
                    painter.drawText(x_pos, y_pos, char)
                    y_pos += line_height
            elif self.snap_edge == 'top':
                painter.save()
                painter.drawText(15, self.height() - 12, self.title)
                painter.restore()

    def get_resize_edges(self, pos):
        margin = 12
        edges = ""
        if pos.y() > self.height() - margin: edges += "bottom"
        elif pos.y() < margin: edges += "top"
        if pos.x() > self.width() - margin: edges += "right"
        elif pos.x() < margin: edges += "left"
        return edges

    def update_cursor(self, edges):
        if edges in ("bottomright", "topleft"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges in ("bottomleft", "topright"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif "left" in edges or "right" in edges:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif "top" in edges or "bottom" in edges:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self.get_resize_edges(event.pos())
            if edges:
                self._is_resizing = True
                self._resize_edges = edges
                self._start_pos = event.globalPosition().toPoint()
                self._resize_start_geometry = self.geometry()
            elif not self.list_widget.geometry().contains(event.pos()):
                self._is_tracking = True
                self._start_pos = event.globalPosition().toPoint() - self.pos()
                self.animation.stop()
                if self.is_collapsed:
                    self.is_collapsed = False
                    self.snap_edge = None
                    self.set_content_visible(True)
                    self.update()

    def mouseMoveEvent(self, event):
        if self._is_resizing:
            from PyQt6.QtCore import QRect
            diff = event.globalPosition().toPoint() - self._start_pos
            rect = QRect(self._resize_start_geometry)
            
            if "bottom" in self._resize_edges: rect.setBottom(self._resize_start_geometry.bottom() + diff.y())
            if "right" in self._resize_edges: rect.setRight(self._resize_start_geometry.right() + diff.x())
            if "top" in self._resize_edges: rect.setTop(self._resize_start_geometry.top() + diff.y())
            if "left" in self._resize_edges: rect.setLeft(self._resize_start_geometry.left() + diff.x())
                
            if rect.width() < 180: rect.setWidth(180)
            if rect.height() < 180: rect.setHeight(180)
                
            self.setGeometry(rect)
            return

        if self._is_tracking:
            self.move(event.globalPosition().toPoint() - self._start_pos)
            return

        edges = self.get_resize_edges(event.pos())
        self.update_cursor(edges)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_resizing:
                self._is_resizing = False
                self.save_position()
            elif self._is_tracking:
                self._is_tracking = False
                self.expanded_pos = self.pos()
                self.save_position()
                self.check_auto_hide()
            
    def save_position(self):
        for f in self.manager.config["fences"]:
            if f["id"] == self.fence_id:
                f["x"] = self.x()
                f["y"] = self.y()
                f["width"] = self.width()
                f["height"] = self.height()
                save_config(self.manager.config)
                break

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            if self.is_collapsed:
                self.is_collapsed = False
                self.snap_edge = None
                self.set_content_visible(True)
                self.animation.setEndValue(self.expanded_pos)
                self.animation.start()
                self.update()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def enterEvent(self, event):
        if self.is_collapsed:
            self.is_collapsed = False
            self.snap_edge = None
            self.set_content_visible(True)
            self.animation.setEndValue(self.expanded_pos)
            self.animation.start()
            self.update()

    def leaveEvent(self, event):
        if not self._is_tracking and not self._is_resizing and not getattr(self, '_is_menu_open', False):
            self.check_auto_hide()
            
    def set_content_visible(self, visible):
        self.label.setVisible(visible)
        self.list_widget.setVisible(visible)

    def check_auto_hide(self):
        screen_geometry = self.screen().availableGeometry()
        margin = 30
        sliver_size = 35
        
        self.snap_edge = None
        if self.y() < margin:
            self.snap_edge = 'top'
            self.expanded_pos = QPoint(self.x(), 0)
            self.animation.setEndValue(QPoint(self.x(), sliver_size - self.height()))
        elif self.x() < margin:
            self.snap_edge = 'left'
            self.expanded_pos = QPoint(0, self.y())
            self.animation.setEndValue(QPoint(sliver_size - self.width(), self.y()))
        elif self.x() + self.width() > screen_geometry.width() - margin:
            self.snap_edge = 'right'
            self.expanded_pos = QPoint(screen_geometry.width() - self.width(), self.y())
            self.animation.setEndValue(QPoint(screen_geometry.width() - sliver_size, self.y()))
            
        if self.snap_edge:
            self.is_collapsed = True
            self.set_content_visible(False)
            self.animation.start()
            self.update()
