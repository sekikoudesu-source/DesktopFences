from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QSlider, QPushButton,
    QTabWidget, QWidget, QCheckBox, QLabel, QComboBox
)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("⚙️ Fences 设置面板")
        self.setFixedSize(450, 360)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1d24;
                color: #e1e4ea;
                font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                background-color: #222630;
                padding: 10px;
            }
            QTabBar::tab {
                background: #181b22;
                color: #9aa4b8;
                padding: 8px 18px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #222630;
                color: #3897f0;
                font-weight: bold;
            }
            QLabel {
                color: #d1d5db;
                font-size: 13px;
            }
            QCheckBox {
                color: #e1e4ea;
                font-size: 13px;
                padding: 8px 0px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #333947;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QComboBox {
                background-color: #181b22;
                color: #e1e4ea;
                border: 1px solid #333947;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1086e3;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget(self)
        
        # --- Tab 1: 外观与视觉 (Appearance) ---
        tab_appearance = QWidget()
        app_layout = QFormLayout(tab_appearance)
        app_layout.setSpacing(15)
        
        # 全局透明度
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 255)
        self.opacity_slider.setValue(self.manager.config.get("opacity", 150))
        self.opacity_label = QLabel(str(self.manager.config.get("opacity", 150)))
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        
        op_h_layout = QHBoxLayout()
        op_h_layout.addWidget(self.opacity_slider)
        op_h_layout.addWidget(self.opacity_label)
        app_layout.addRow("🎨 全局透明度:", op_h_layout)
        
        # 圆角弧度
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(4, 24)
        self.radius_slider.setValue(self.manager.config.get("corner_radius", 12))
        self.radius_label = QLabel(f"{self.manager.config.get('corner_radius', 12)} px")
        self.radius_slider.valueChanged.connect(self._on_radius_changed)
        
        rad_h_layout = QHBoxLayout()
        rad_h_layout.addWidget(self.radius_slider)
        rad_h_layout.addWidget(self.radius_label)
        app_layout.addRow("⭕ 圆角弧度:", rad_h_layout)
        
        # 标题字号
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(12, 18)
        self.font_slider.setValue(self.manager.config.get("header_font_size", 14))
        self.font_label = QLabel(f"{self.manager.config.get('header_font_size', 14)} px")
        self.font_slider.valueChanged.connect(self._on_font_size_changed)
        
        font_h_layout = QHBoxLayout()
        font_h_layout.addWidget(self.font_slider)
        font_h_layout.addWidget(self.font_label)
        app_layout.addRow("🔤 标题字号:", font_h_layout)
        
        # 风格主题
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认深色玻璃 (Classic Dark)", "优雅浅色玻璃 (Light Glass)", "赛博霓虹 (Cyber Neon)", "极简暗黑 (Minimal Dark)"])
        current_theme = self.manager.config.get("theme", "default")
        theme_map = {"default": 0, "light": 1, "neon": 2, "minimal": 3}
        self.theme_combo.setCurrentIndex(theme_map.get(current_theme, 0))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        app_layout.addRow("🎭 全局主题:", self.theme_combo)
        
        self.tabs.addTab(tab_appearance, "🎨 外观样式")
        
        # --- Tab 2: 快捷交互 (Interactions) ---
        tab_interactions = QWidget()
        int_layout = QVBoxLayout(tab_interactions)
        int_layout.setSpacing(12)
        
        # 双击桌面显隐
        self.chk_double_click = QCheckBox("⚡ 双击桌面空白处隐藏/显示所有收纳盒")
        self.chk_double_click.setChecked(self.manager.config.get("double_click_hide", True))
        self.chk_double_click.toggled.connect(self.manager.update_double_click_hide)
        int_layout.addWidget(self.chk_double_click)
        
        # 移出自动卷帘
        self.chk_rollup = QCheckBox("📜 移出鼠标自动卷帘折叠收纳盒 (Roll-up)")
        self.chk_rollup.setChecked(self.manager.config.get("rollup_on_leave", False))
        self.chk_rollup.toggled.connect(self.manager.update_rollup_mode)
        int_layout.addWidget(self.chk_rollup)
        
        # 防误触锁定
        self.chk_lock = QCheckBox("🔒 防误触锁定收纳盒位置与大小 (Lock Position)")
        self.chk_lock.setChecked(self.manager.config.get("lock_positions", False))
        self.chk_lock.toggled.connect(self.manager.update_lock_positions)
        int_layout.addWidget(self.chk_lock)
        
        int_layout.addStretch()
        
        self.tabs.addTab(tab_interactions, "⚡ 快捷交互")
        
        main_layout.addWidget(self.tabs)
        
        # 底部确定按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("完成")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        main_layout.addLayout(btn_layout)

    def _on_opacity_changed(self, val):
        self.opacity_label.setText(str(val))
        self.manager.update_opacity(val)

    def _on_radius_changed(self, val):
        self.radius_label.setText(f"{val} px")
        self.manager.update_corner_radius(val)

    def _on_font_size_changed(self, val):
        self.font_label.setText(f"{val} px")
        self.manager.update_header_font_size(val)

    def _on_theme_changed(self, index):
        theme_keys = ["default", "light", "neon", "minimal"]
        if 0 <= index < len(theme_keys):
            self.manager.change_global_theme(theme_keys[index])
