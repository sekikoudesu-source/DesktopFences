import os
import shutil
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QMessageBox, QListWidgetItem, QFileIconProvider
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QFileInfo, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QAction, QIcon
import random

from core.i18n import _

from core.config import DATA_DIR, save_config, save_restore_map
from ui.fence_list import FenceListWidget
from utils.win32 import robust_move, open_file_safely

from collections import OrderedDict

ICON_CACHE = OrderedDict()
MAX_CACHE_SIZE = 500
from PyQt6.QtWidgets import QFileIconProvider
SHARED_ICON_PROVIDER = QFileIconProvider()

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

import time
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QPen, QBrush

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
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        x = fence_config.get("x", 100)
        y = fence_config.get("y", 100)
        w = fence_config.get("width", 320)
        h = fence_config.get("height", 400)
        self.expanded_pos = QPoint(x, y)
        self.setGeometry(x, y, w, h)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        self.label = QLabel(self.title, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.border_timer = QTimer(self)
        self.border_timer.timeout.connect(self.update)
        
        self._drag_timer = QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.timeout.connect(self._on_drag_finished)
        self.label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.label.customContextMenuRequested.connect(self.show_title_context_menu)
        layout.addWidget(self.label)
        
        self.list_widget = FenceListWidget(self.folder_path, self)
        self.list_widget.itemDoubleClicked.connect(self.open_file)
        layout.addWidget(self.list_widget)
        
        self.label.installEventFilter(self)
        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.installEventFilter(self)
        self.list_widget.viewport().installEventFilter(self)
        
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
        self._last_particle_time = 0.0

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
        self.list_widget.apply_theme("default")
        radius = self.manager.config.get("corner_radius", 12)
        font_size = self.manager.config.get("header_font_size", 13)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.95);
                font-family: 'Segoe UI Variable Text', 'Segoe UI', 'Inter', -apple-system, sans-serif;
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 5px 14px;
                margin-left: 2px;
                margin-right: 2px;
            }}
        """)
        if hasattr(self, 'border_timer'):
            self.border_timer.stop()
        self.update()

    def show_title_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: rgba(20, 20, 22, 0.95); color: rgba(255, 255, 255, 0.9); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; }
            QMenu::item { padding: 6px 24px; border-radius: 4px; margin: 2px 4px; }
            QMenu::item:selected { background-color: rgba(255, 255, 255, 0.1); }
        """)
        ren_action = QAction(_("✏️ 重命名收纳盒 (Rename)"), self)
        ren_action.triggered.connect(self.rename_fence)
        menu.addAction(ren_action)
        
        del_action = QAction(_("❌ 解散收纳盒 (Destroy)"), self)
        del_action.triggered.connect(self.destroy_fence)
        menu.addAction(del_action)
        menu.exec(self.label.mapToGlobal(pos))
        
    def rename_fence(self):
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, _("重命名收纳盒"), _("输入新名称:"), text=self.title)
        if ok and new_name and new_name != self.title:
            self.title = new_name
            self.manager.config["fences"] = [f if f["id"] != self.fence_id else {**f, "title": new_name} for f in self.manager.config["fences"]]
            save_config(self.manager.config)
            self.load_files() # Refresh title label
        
    def destroy_fence(self):
        reply = QMessageBox.question(self, _("确认解散"), _("确定要解散【{title}】吗？\n收纳盒内的文件将保持在桌面上原有位置！").format(title=self.title), 
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
            
            icon = get_icon_for_file(file_path, SHARED_ICON_PROVIDER)
            
            display_name = os.path.splitext(filename)[0]
            elided_text = fm.elidedText(display_name, Qt.TextElideMode.ElideMiddle, 75)
            
            item = QListWidgetItem(icon, elided_text)
            item.setToolTip(filename)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_widget.addItem(item)
            
        count = self.list_widget.count()
        self.label.setText(f"""<span style="font-weight: 600; font-size: 14px; color: rgba(255,255,255,0.95);">{self.title}</span> &nbsp;<span style="font-weight: 500; font-size: 11px; color: rgba(255,255,255,0.4);">{count} ITEMS</span>""")
                
    def open_file(self, item):
        file_path = os.path.join(self.folder_path, item.toolTip())
        open_file_safely(file_path)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        opacity = self.manager.config.get("opacity", 64)
        rect = self.rect()
        radius = float(self.manager.config.get("corner_radius", 12))
        
        # Premium 3D Cold Luxury Glassmorphism
        # Base gradient with angled lighting
        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0.0, QColor(38, 38, 42, opacity + 60))
        grad.setColorAt(0.5, QColor(24, 24, 26, opacity + 45))
        grad.setColorAt(1.0, QColor(14, 14, 16, opacity + 65))
        painter.setBrush(grad)
        
        if self.underMouse():
            border_pen = QPen(QColor(255, 255, 255, 55), 1)
        else:
            border_pen = QPen(QColor(255, 255, 255, 25), 1)
        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, radius, radius)
        
        # --- GEOMETRIC ELEMENTS (Dark Tech / Architectural Vibe) ---
        painter.save()
        
        # 1. Large geometric accent (Faint dashed circle top-right)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect.width() - 80, -40, 160, 160)
        
        # 2. Geometric Accent Bar (Neon Cyan)
        painter.fillRect(rect.width() // 2 - 16, 0, 32, 2, QColor(0, 220, 255, 180))
        
        # 3. Precise Corner Reticles (Crosshairs)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False) # Crisp 1px lines
        cross_size = 5
        margin = int(radius) + 12
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        
        # Top-Left, Top-Right, Bottom-Left, Bottom-Right
        corners = [
            (margin, margin),
            (rect.width() - margin, margin),
            (margin, rect.height() - margin),
            (rect.width() - margin, rect.height() - margin)
        ]
        for cx, cy in corners:
            painter.drawLine(cx - cross_size, cy, cx + cross_size, cy)
            painter.drawLine(cx, cy - cross_size, cx, cy + cross_size)
            
        # 4. Subtle Dot Matrix Grid (Fade out opacity)
        painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
        dot_spacing = 24
        for x in range(margin, rect.width() - margin, dot_spacing):
            for y in range(margin + 30, rect.height() - margin, dot_spacing):
                painter.drawPoint(x, y)
                
        painter.restore()
        # --- END GEOMETRIC ELEMENTS ---
        
        # Directional Lighting Highlight (top-left)
        light_grad = QLinearGradient(0, 0, rect.width() * 0.7, rect.height() * 0.7)
        light_grad.setColorAt(0.0, QColor(255, 255, 255, 18))
        light_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(light_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

        # Inner highlight for liquid glass edge refraction
        inner_rect = rect.adjusted(1, 1, -1, -1)
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(inner_rect, max(0, radius - 1), max(0, radius - 1))
        
        if self.is_collapsed and getattr(self, 'snap_edge', None):
            painter.setPen(QColor(255, 255, 255, 200))
            font = painter.font()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            
            if self.snap_edge in ('left', 'right'):
                fm = painter.fontMetrics()
                line_height = fm.height()
                y_pos = max(30, (self.height() - len(self.title) * line_height) // 2)
                for char in self.title:
                    char_width = fm.horizontalAdvance(char)
                    if self.snap_edge == 'left':
                        x_pos = self.width() - 35 + (35 - char_width) // 2
                    else:
                        x_pos = (35 - char_width) // 2
                    painter.drawText(x_pos, y_pos, char)
                    y_pos += line_height
            elif self.snap_edge == 'top':
                fm = painter.fontMetrics()
                text_width = fm.horizontalAdvance(self.title)
                x_pos = (self.width() - text_width) // 2
                painter.drawText(x_pos, self.height() - 12, self.title)

        for p in self.particles:
            alpha = int((p.life / p.max_life) * p.color.alpha())
            c = QColor(p.color)
            c.setAlpha(alpha)
            painter.setBrush(c)
            painter.setPen(Qt.PenStyle.NoPen)
            current_size = max(1.0, p.size * (p.life / p.max_life))
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawEllipse(QPointF(p.x, p.y), current_size, current_size)



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
            if hasattr(self, 'list_widget'):
                self.list_widget.unsetCursor()
                self.list_widget.viewport().unsetCursor()

    def mousePressEvent(self, event):
        if self.manager.config.get("lock_positions", False):
            return
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
        if not getattr(self, 'is_collapsed', False):
            self.expanded_pos = self.pos()
        if hasattr(self, '_drag_timer'):
            self._drag_timer.start(300)
            
    def _on_drag_finished(self):
        # Unlock the window size so Qt can properly apply the new monitor's PerMonitorV2 scaling
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        
        if not self.is_collapsed:
            self.expanded_pos = self.pos()
        self.save_position()
        from PyQt6.QtGui import QCursor
        # Do not immediately hide if the user's mouse is still inside the widget after dropping it
        if not self.geometry().contains(QCursor.pos()):
            self.check_auto_hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def mouseMoveEvent(self, event):
        if self.manager.config.get("lock_positions", False):
            self.unsetCursor()
            return
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

        # Motion must be motivated. Removed unprompted continuous stardust on hover.

        edges = self.get_resize_edges(event.pos())
        self.update_cursor(edges)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_resizing:
                self._is_resizing = False
                self.save_position()
            
    def save_position(self):
        pos = getattr(self, 'expanded_pos', self.pos())
        for f in self.manager.config["fences"]:
            if f["id"] == self.fence_id:
                f["x"] = pos.x()
                f["y"] = pos.y()
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
        if self.manager.config.get("rollup_on_leave", False) and getattr(self, "is_rolled_up", False):
            self.is_rolled_up = False
            fence_config = next((fc for fc in self.manager.config["fences"] if fc["id"] == self.fence_id), None)
            target_h = fence_config.get("height", 400) if fence_config else 400
            self.list_widget.setVisible(True)
            self.resize(self.width(), target_h)
            self.update()

        if self.is_collapsed:
            self.is_collapsed = False
            self.snap_edge = None
            self.set_content_visible(True)
            self.animation.setEndValue(self.expanded_pos)
            self.animation.start()
            self.update()

    def eventFilter(self, watched, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.MouseMove:
            if watched in (self.list_widget, self.list_widget.viewport(), self.label):
                if self.cursor().shape() != Qt.CursorShape.ArrowCursor:
                    self.unsetCursor()
                    if hasattr(self, 'list_widget'):
                        self.list_widget.unsetCursor()
                        self.list_widget.viewport().unsetCursor()
                
                # Motion must be motivated. Removed continuous stardust on hover.
        return super().eventFilter(watched, event)

    def leaveEvent(self, event):
        from PyQt6.QtGui import QCursor
        # Windows translucent hit-testing might falsely report the mouse leaving 
        # if it hovers over a fully transparent pixel. We enforce a strict geometric bound check.
        if self.geometry().contains(QCursor.pos()):
            return
            
        self.unsetCursor()
        if hasattr(self, 'list_widget'):
            self.list_widget.unsetCursor()
            self.list_widget.viewport().unsetCursor()

        if self.manager.config.get("rollup_on_leave", False) and not getattr(self, "is_rolled_up", False):
            if not self._is_resizing and not getattr(self, '_is_menu_open', False):
                self.is_rolled_up = True
                self.list_widget.setVisible(False)
                self.resize(self.width(), 48)
                self.update()
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
            self.is_collapsed = True
            self.set_content_visible(False)
            self.animation.start()
            self.update()

    def update_particles(self):
        if self.is_collapsed:
            self.particles.clear()
            self.particle_timer.stop()
            return

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

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.showNormal()
                return
        super().changeEvent(event)


