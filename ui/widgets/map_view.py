from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        lbl = QLabel("🗺️ MAP / TELEMETRY VIEW")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #00FF66; font-size: 16px; font-weight: bold;")
        
        layout.addWidget(lbl)