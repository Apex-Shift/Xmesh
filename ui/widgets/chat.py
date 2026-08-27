"""Live chat widget – displays intercepted TEXT_MESSAGE packets and allows broadcasting."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ChatWidget(QWidget):
    def __init__(self, signals=None, parent=None) -> None:
        super().__init__(parent)
        self.signals = signals
        self._build_ui()

        if self.signals:
            self.signals.message_received.connect(self.add_message)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("Waiting for channel traffic…")
        self.chat_display.setObjectName("ChatDisplay")
        layout.addWidget(self.chat_display)

        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a broadcast message and press Enter…")
        self.input_field.returnPressed.connect(self.send_message)

        self.send_btn = QPushButton("SEND")
        self.send_btn.setFixedWidth(90)
        self.send_btn.clicked.connect(self.send_message)

        input_row.addWidget(self.input_field)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

    def send_message(self) -> None:
        text = self.input_field.text().strip()
        if text and self.signals:
            self.signals.send_message_requested.emit(text)
            self.input_field.clear()

    def add_message(self, packet: dict) -> None:
        sender = packet.get("from_node", "UNKNOWN")
        msg = packet.get("data", "")
        if isinstance(msg, dict):
            msg = str(msg)
        if not msg:
            return

        ts = datetime.now().strftime("%H:%M:%S")
        is_self = "(YOU)" in str(sender)
        colour = "#00FF66" if is_self else "#C5D0DE"
        html = (
            f'<span style="color:#5A6A7A">[{ts}]</span> '
            f'<span style="color:{colour};font-weight:bold">{sender}</span>: '
            f'<span style="color:#E8EEF5">{msg}</span>'
        )
        self.chat_display.append(html)
