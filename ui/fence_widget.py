import os
import shutil
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QMessageBox, QListWidgetItem, QFileIconProvider
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QFileInfo, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QAction, QIcon
import random

from core.config import DATA_DIR, save_config, save_restore_map
from ui.fence_list import FenceListWidget
from utils.win32 import robust_move, open_file_safely

from collections import OrderedDict

ICON_CACHE = OrderedDict()
MAX_CACHE_SIZE = 500

class Particle:
    def __init__(self, x, y, vx, vy, life, color, size):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size


def get_icon_for_file(file_path, provider):
    ext = os.path.splitext(file_path)[1].lower()
    
    is_unique = ext in [".exe", ".lnk", ".url"]
    cache_key = file_path if is_unique else ext

    if cache_key in ICON_CACHE:
        # Move to end to mark as most recently used
        icon = ICON_CACHE.pop(cache_key)
        ICON_CACHE[cache_key] = icon
        return icon

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
        
    if len(ICON_CACHE) >= MAX_CACHE_SIZE:
        ICON_CACHE.popitem(last=False)
        
    ICON_CACHE[cache_key] = icon
    return icon

class FenceWidget(QWidget):
    def __init__(self, fence_config, manager):
        super().__init__()
        self.manager = manager
        self.fence_id = fence_config["id"]
        self.title = fence_config["title"]
        self.is_virtual = fence_config.get("is_virtual", False)
        if self.is_virtual:
            self.folder_path = self.manager.desktop_dir
        else:
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
        
        self._drag_timer = QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.timeout.connect(self._on_drag_finished)
        self.label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.label.customContextMenuRequested.connect(self.show_title_context_menu)
        layout.addWidget(self.label)
        
        self.list_widget = FenceListWidget(self.folder_path, self)
        self.list_widget.itemDoubleClicked.connect(self.open_file)
        layout.addWidget(self.list_widget)
        
        self.apply_theme()
        
        self.load_files()
        
        if not self.is_virtual:
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

        self.particles = []
        self.particle_timer = QTimer(self)
        self.particle_timer.timeout.connect(self.update_particles)

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.is_collapsed = False
        self.snap_edge = None
        self.expanded_pos = self.pos()

    def apply_theme(self):
        theme = self.manager.config.get("theme", "default")
        self.list_widget.apply_theme(theme)
        
        if theme == "cute":
            self.label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 16px; font-family: 'Comic Sans MS', sans-serif; background: transparent;")
        elif theme == "aurora":
            self.label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 16px; font-family: 'Segoe UI', sans-serif; background: transparent;")
        elif theme == "mecha":
            self.label.setStyleSheet("color: #ff6600; font-weight: 900; font-size: 16px; font-family: 'Arial Black', sans-serif; background: transparent; padding-left: 5px;")
        elif theme == "cyberpunk":
            self.label.setStyleSheet("color: #00ffff; font-weight: bold; font-size: 16px; font-family: 'Impact', sans-serif; background: transparent; text-shadow: 0px 0px 10px #00ffff;")
        elif theme == "holographic":
            self.label.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 16px; font-family: 'Consolas', monospace; background: transparent;")
        else:
            self.label.setStyleSheet("color: white; font-weight: bold; font-size: 16px; background: transparent;")
            
        self.update()

    def show_title_context_menu(self, pos):
        menu = QMenu(self)
        theme = self.manager.config.get("theme", "default")
        if theme == "aurora":
            menu.setStyleSheet("""
                QMenu { background-color: rgba(30, 10, 45, 0.9); color: white; border: 1px solid #7a28cb; border-radius: 8px; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: #4a0e4e; } 
            """)
        elif theme == "mecha":
            menu.setStyleSheet("""
                QMenu { background-color: #1a1a1a; color: #ff6600; border: 2px solid #ff6600; font-family: 'Arial Black'; font-weight: 900; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: #ff6600; color: #1a1a1a; } 
            """)
        elif theme == "cyberpunk":
            menu.setStyleSheet("""
                QMenu { background-color: #0b0b1a; color: #00ffff; border: 2px solid #ff00ff; font-family: 'Impact'; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: #ff00ff; color: #000000; } 
            """)
        elif theme == "holographic":
            menu.setStyleSheet("""
                QMenu { background-color: rgba(0, 20, 30, 0.9); color: #00e5ff; border: 1px solid #00e5ff; font-family: 'Consolas'; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: rgba(0, 229, 255, 0.3); } 
            """)
        elif theme == "cute":
            menu.setStyleSheet("""
                QMenu { background-color: #f0f8ff; color: #66b2ff; border: 1px solid #a2d2ff; border-radius: 5px; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: #dbe9f4; } 
            """)
        else:
            menu.setStyleSheet("""
                QMenu { background-color: #2c2c2c; color: white; border: 1px solid #555; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: #d73a49; } 
            """)
            
        theme_menu = menu.addMenu("🎨 切换主题 (Themes)")
        themes = {
            "default": "默认风格 (Glassmorphism)",
            "cute": "可爱风 (Cute)",
            "aurora": "极光毛玻璃 (Aurora Glass)",
            "mecha": "硬核机甲 (Sci-Fi Mecha)",
            "cyberpunk": "赛博霓虹 (Cyberpunk Neon)",
            "holographic": "全息投影 (Holographic HUD)"
        }
        for t_key, t_name in themes.items():
            act = theme_menu.addAction(t_name)
            act.setCheckable(True)
            if theme == t_key:
                act.setChecked(True)
            act.triggered.connect(lambda checked, k=t_key: self.manager.change_global_theme(k))
            
        del_action = QAction("❌ 解散收纳盒 (Destroy)", self)
        del_action.triggered.connect(self.destroy_fence)
        menu.addAction(del_action)
        menu.exec(self.label.mapToGlobal(pos))
        
    def destroy_fence(self):
        reply = QMessageBox.question(self, "确认解散", f"确定要解散【{self.title}】吗？\n收纳盒内的文件将保持在桌面上原有位置！", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        
        self.set_content_visible(False)
        self.label.setVisible(False)
        self.list_widget.setVisible(False)
        self.emit_fireworks()
        QTimer.singleShot(1500, self._execute_destroy)
            
    def _execute_destroy(self):
        self.manager.config["fences"] = [f for f in self.manager.config["fences"] if f["id"] != self.fence_id]
        save_config(self.manager.config)
        
        if self in self.manager.fences:
            self.manager.fences.remove(self)
            
        # Reconcile to assign files to unclassified fence
        self.manager.reconcile_desktop_files()
        
        self.close()
        self.deleteLater()

    def load_files(self):
        if not os.path.exists(self.folder_path): return
            
        self.list_widget.clear()
        provider = QFileIconProvider()
        fm = self.list_widget.fontMetrics()
        
        if self.is_virtual:
            fence_config = next((fc for fc in self.manager.config["fences"] if fc["id"] == self.fence_id), None)
            filenames = fence_config.get("files", []) if fence_config else []
        else:
            try:
                filenames = os.listdir(self.folder_path)
            except Exception:
                filenames = []
        
        for filename in filenames:
            if filename.lower() == "desktop.ini": continue
            if filename.startswith("~$"): continue
                
            file_path = os.path.join(self.folder_path, filename)
            if not os.path.exists(file_path): continue
            
            icon = get_icon_for_file(file_path, provider)
            
            display_name = os.path.splitext(filename)[0]
            elided_text = fm.elidedText(display_name, Qt.TextElideMode.ElideMiddle, 75)
            
            item = QListWidgetItem(icon, elided_text)
            item.setToolTip(filename)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_widget.addItem(item)
                
    def open_file(self, item):
        file_path = os.path.join(self.folder_path, item.toolTip())
        open_file_safely(file_path)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        theme = self.manager.config.get("theme", "default")
        opacity = self.manager.config.get("opacity", 64)
        rect = self.rect()
        
        if theme == "cute":
            grad = QLinearGradient(0, 0, rect.width(), rect.height())
            grad.setColorAt(0.0, QColor(162, 210, 255, opacity + 20))
            grad.setColorAt(1.0, QColor(210, 235, 255, opacity + 20))
            painter.setBrush(grad)
            painter.setPen(QPen(QColor(130, 190, 255, 150), 2))
            painter.drawRoundedRect(rect, 15.0, 15.0)
        elif theme == "aurora":
            grad = QLinearGradient(0, 0, rect.width(), rect.height())
            grad.setColorAt(0.0, QColor(48, 12, 66, opacity + 40))   # Deep Purple
            grad.setColorAt(0.5, QColor(25, 33, 76, opacity + 40))   # Midnight Blue
            grad.setColorAt(1.0, QColor(10, 68, 89, opacity + 40))   # Deep Teal
            painter.setBrush(grad)
            painter.setPen(QPen(QColor(255, 255, 255, 80), 1))       # Soft white inner glow border
            painter.drawRoundedRect(rect, 12.0, 12.0)
            
            # Subtle highlight on top edge
            painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
            painter.drawLine(rect.left() + 12, rect.top(), rect.right() - 12, rect.top())

        elif theme == "mecha":
            from PyQt6.QtGui import QPainterPath
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(20, 20, 20, opacity + 60))
            
            # Draw industrial chamfered corners
            path = QPainterPath()
            cut = 20.0
            path.moveTo(rect.left() + cut, rect.top())
            path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom() - cut)
            path.lineTo(rect.right() - cut, rect.bottom())
            path.lineTo(rect.left(), rect.bottom())
            path.lineTo(rect.left(), rect.top() + cut)
            path.closeSubpath()
            
            painter.setPen(QPen(QColor(255, 102, 0, 200), 2)) # Hazard Orange
            painter.drawPath(path)
            
            # Draw subtle hazard stripes
            painter.setBrush(Qt.BrushStyle.BDiagPattern)
            painter.setPen(Qt.PenStyle.NoPen)
            # Orange stripes brush
            # But QBrush with pattern takes color for the pattern
            # We'll just draw a small accent rect with stripes
            painter.setBrush(QColor(255, 102, 0, 80))
            painter.drawRect(rect.right() - 25, rect.top() + 5, 20, 10)

        elif theme == "cyberpunk":
            from PyQt6.QtGui import QPainterPath
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            # Solid Dark Cyberpunk Base
            painter.setBrush(QColor(20, 20, 25, opacity + 100))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Draw cyberpunk base with chopped bottom-right corner
            path = QPainterPath()
            cut = 30.0
            path.moveTo(rect.left(), rect.top())
            path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom() - cut)
            path.lineTo(rect.right() - cut, rect.bottom())
            path.lineTo(rect.left(), rect.bottom())
            path.closeSubpath()
            painter.drawPath(path)
            
            # Edgerunner Yellow Accent Top Border
            painter.setBrush(QColor(252, 238, 10, 255))
            painter.drawRect(rect.left(), rect.top(), int(rect.width() * 0.6), 5)
            
            # Neon Cyan Accent Bottom-Right cut
            painter.setPen(QPen(QColor(0, 229, 255, 255), 4))
            painter.drawLine(int(rect.right() - cut), rect.bottom(), rect.right(), int(rect.bottom() - cut))
            
            # Neon Pink Accent Left Border
            painter.setBrush(QColor(255, 0, 85, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect.left(), rect.top() + 30, 4, int(rect.height() * 0.4))

        elif theme == "holographic":
            from PyQt6.QtGui import QPainterPath
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setBrush(QColor(0, 15, 25, opacity + 60))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 15.0, 15.0)
            
            # Glow effect via multiple overlapping rounded rects
            glow_colors = [
                QColor(0, 229, 255, 20),
                QColor(0, 229, 255, 60),
                QColor(0, 229, 255, 120),
                QColor(0, 229, 255, 255)
            ]
            for i, c in enumerate(glow_colors):
                painter.setPen(QPen(c, 1))
                # Adjust radius slightly for inner rects
                painter.drawRoundedRect(rect.adjusted(i, i, -i, -i), max(0, 15.0 - i), max(0, 15.0 - i))
            
            # Draw scanlines overlay, clipped perfectly to the rounded corners
            painter.save()
            path = QPainterPath()
            path.addRoundedRect(QRectF(rect), 15.0, 15.0)
            painter.setClipPath(path)
            painter.setPen(QPen(QColor(0, 229, 255, 15), 1))
            for y in range(rect.top(), rect.bottom(), 4):
                painter.drawLine(rect.left(), y, rect.right(), y)
            painter.restore()
        else: # default
            painter.setBrush(QColor(0, 0, 0, opacity))
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
            painter.drawRoundedRect(rect, 10.0, 10.0)
        
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

        for p in self.particles:
            alpha = int((p.life / p.max_life) * p.color.alpha())
            c = QColor(p.color)
            c.setAlpha(alpha)
            painter.setBrush(c)
            painter.setPen(Qt.PenStyle.NoPen)
            current_size = max(1.0, p.size * (p.life / p.max_life))
            
            theme = self.manager.config.get("theme", "default")
            if theme == "aurora":
                # Soft floating orbs
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.drawEllipse(QPointF(p.x, p.y), current_size, current_size)
            elif theme == "mecha":
                # Industrial sparks
                painter.setPen(QPen(c, 2))
                painter.drawLine(int(p.x), int(p.y), int(p.x + current_size*2), int(p.y + current_size*2))
            elif theme == "cyberpunk":
                # Glitch particles
                painter.setPen(QPen(c, 2))
                painter.drawLine(int(p.x), int(p.y), int(p.x + current_size*3), int(p.y))
            elif theme == "holographic":
                # Digital matrix glitch lines
                painter.setPen(QPen(c, 1))
                painter.drawLine(int(p.x), int(p.y), int(p.x + current_size*4), int(p.y))


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
                # Delegate entirely to the native OS window manager for perfectly smooth 
                # cross-monitor multi-DPI dragging without globalPosition jumps.
                if self.window().windowHandle():
                    # Lock the window's logical size during the drag to prevent Qt's PerMonitorV2
                    # DPI engine from resizing the window mid-drag, which causes infinite jitter loops.
                    self.setFixedSize(self.size())
                    self.window().windowHandle().startSystemMove()
                self.animation.stop()
                if self.is_collapsed:
                    self.is_collapsed = False
                    self.snap_edge = None
                    self.set_content_visible(True)
                    self.update()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, '_drag_timer'):
            self._drag_timer.start(300)
        if hasattr(self, 'title') and self.title_text == "工作与文档":
            pass
            
    def _on_drag_finished(self):
        # Unlock the window size so Qt can properly apply the new monitor's PerMonitorV2 scaling
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        
        self.expanded_pos = self.pos()
        self.save_position()
        from PyQt6.QtGui import QCursor
        # Do not immediately hide if the user's mouse is still inside the widget after dropping it
        if not self.geometry().contains(QCursor.pos()):
            self.check_auto_hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'title') and self.title_text == "工作与文档":
            pass

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

        if not self.is_collapsed and not self._is_resizing and random.random() < 0.3:
            self.emit_stardust(event.pos())

        edges = self.get_resize_edges(event.pos())
        self.update_cursor(edges)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_resizing:
                self._is_resizing = False
                self.save_position()
            
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
        from PyQt6.QtGui import QCursor
        # Windows translucent hit-testing might falsely report the mouse leaving 
        # if it hovers over a fully transparent pixel. We enforce a strict geometric bound check.
        if self.geometry().contains(QCursor.pos()):
            return
            
        if not self._is_tracking and not self._is_resizing and not getattr(self, '_is_menu_open', False):
            self.check_auto_hide()
            
    def set_content_visible(self, visible):
        self.label.setVisible(visible)
        self.list_widget.setVisible(visible)

    def get_current_screen_geometry(self):
        from PyQt6.QtWidgets import QApplication
        widget_rect = self.geometry()
        screens = QApplication.screens()
        
        max_area = -1
        best_screen = None
        
        for screen in screens:
            intersect = screen.availableGeometry().intersected(widget_rect)
            area = intersect.width() * intersect.height()
            if area > max_area:
                max_area = area
                best_screen = screen
                
        if max_area > 0 and best_screen:
            return best_screen.availableGeometry()
            
        # Fallback: find closest screen
        min_dist = float('inf')
        best_screen = screens[0]
        center = widget_rect.center()
        
        for screen in screens:
            rect = screen.availableGeometry()
            dx = center.x() - rect.center().x()
            dy = center.y() - rect.center().y()
            dist = dx*dx + dy*dy
            if dist < min_dist:
                min_dist = dist
                best_screen = screen
                
        return best_screen.availableGeometry()

    def check_auto_hide(self):
        screen_geometry = self.get_current_screen_geometry()
        margin = 30
        sliver_size = 35
        
        if hasattr(self, 'title') and self.title_text == "工作与文档":
            pass
        
        def is_outer_edge(edge):
            from PyQt6.QtWidgets import QApplication
            screens = QApplication.screens()
            if edge == 'top':
                pt = QPoint(self.x() + self.width() // 2, screen_geometry.top() - 1)
            elif edge == 'left':
                pt = QPoint(screen_geometry.left() - 1, self.y() + self.height() // 2)
            elif edge == 'right':
                pt = QPoint(screen_geometry.right() + 1, self.y() + self.height() // 2)
            else:
                return True
            for s in screens:
                if s.geometry().contains(pt):
                    return False
            return True
            
        self.snap_edge = None
        if self.y() <= screen_geometry.top() + margin and is_outer_edge('top'):
            self.snap_edge = 'top'
            self.expanded_pos = QPoint(self.x(), screen_geometry.top())
            self.animation.setEndValue(QPoint(self.x(), screen_geometry.top() + sliver_size - self.height()))
        elif self.x() <= screen_geometry.left() + margin and is_outer_edge('left'):
            self.snap_edge = 'left'
            self.expanded_pos = QPoint(screen_geometry.left(), self.y())
            self.animation.setEndValue(QPoint(screen_geometry.left() + sliver_size - self.width(), self.y()))
        elif self.x() + self.width() >= screen_geometry.right() - margin and is_outer_edge('right'):
            self.snap_edge = 'right'
            self.expanded_pos = QPoint(screen_geometry.right() - self.width() + 1, self.y())
            self.animation.setEndValue(QPoint(screen_geometry.right() - sliver_size + 1, self.y()))
            
        if self.snap_edge:
            if hasattr(self, 'title') and self.title_text == "工作与文档":
                pass
            self.is_collapsed = True
            self.set_content_visible(False)
            self.animation.start()
            self.update()

    def update_particles(self):
        if not self.particles:
            self.particle_timer.stop()
            return
            
        i = 0
        while i < len(self.particles):
            p = self.particles[i]
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            p.vy += 0.2
            if p.life <= 0:
                # O(1) in-place deletion to prevent GC pressure
                self.particles[i] = self.particles[-1]
                self.particles.pop()
            else:
                i += 1
                
        self.update()

    def emit_stardust(self, pos):
        for _ in range(2):
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(-1.5, 0.5)
            life = random.randint(20, 50)
            color = QColor(255, 255, 255, random.randint(100, 200))
            size = random.uniform(1.5, 3.5)
            self.particles.append(Particle(pos.x(), pos.y(), vx, vy, life, color, size))
        if not self.particle_timer.isActive():
            self.particle_timer.start(16)

    def emit_blackhole(self, pos):
        for _ in range(40):
            vx = random.uniform(-6, 6)
            vy = random.uniform(-6, 6)
            life = random.randint(30, 50)
            color = QColor(0, 200, 255, random.randint(150, 255))
            size = random.uniform(2, 5)
            self.particles.append(Particle(pos.x(), pos.y(), vx, vy, life, color, size))
        if not self.particle_timer.isActive():
            self.particle_timer.start(16)

    def emit_fireworks(self):
        cx = self.width() / 2
        cy = self.height() / 2
        for _ in range(150):
            vx = random.uniform(-12, 12)
            vy = random.uniform(-12, 12)
            life = random.randint(40, 80)
            red = random.randint(200, 255)
            green = random.randint(100, 200)
            color = QColor(red, green, 0, 255)
            size = random.uniform(3, 7)
            self.particles.append(Particle(cx, cy, vx, vy, life, color, size))
        if not self.particle_timer.isActive():
            self.particle_timer.start(16)

