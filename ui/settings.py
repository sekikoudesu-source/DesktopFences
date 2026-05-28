from PyQt6.QtWidgets import QDialog, QFormLayout, QSlider, QPushButton
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Fences 设置面板")
        self.setFixedSize(300, 120)
        
        layout = QFormLayout(self)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 255)
        self.opacity_slider.setValue(self.manager.config.get("opacity", 150))
        self.opacity_slider.valueChanged.connect(self.manager.update_opacity)
        
        layout.addRow("全局透明度:", self.opacity_slider)
        
        btn_close = QPushButton("完成")
        btn_close.clicked.connect(self.accept)
        layout.addRow("", btn_close)
