from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton
from PySide6.QtCore import Qt

class ChatWidget(QWidget):
    def __init__(self, signals=None, parent=None):
        super().__init__(parent)
        self.signals = signals
        
        layout = QVBoxLayout(self)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("Waiting for channel traffic...")
        layout.addWidget(self.chat_display)
        
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a broadcast message...")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        
        if self.signals:
            self.signals.message_received.connect(self.add_message)

    def send_message(self):
        text = self.input_field.text().strip()
        if text and self.signals:
            self.signals.send_message_requested.emit(text)
            self.input_field.clear()

    def add_message(self, packet):
        sender = packet.get("from_node", "UNKNOWN")
        msg_text = packet.get("data", "")
        if isinstance(msg_text, dict):
            msg_text = str(msg_text)
            
        if msg_text:
            formatted = f"[{sender}]: {msg_text}"
            self.chat_display.append(formatted)