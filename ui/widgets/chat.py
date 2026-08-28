"""Live chat with search, clear and channel badges."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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
        self.history: list[dict[str, Any]] = []
        self._filter = ""
        self._build_ui()

        if self.signals:
            self.signals.message_received.connect(self.add_message)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Filter messages…")
        self.search.textChanged.connect(self._on_filter)
        toolbar.addWidget(self.search)

        btn_clear_filter = QPushButton("Clear filter")
        btn_clear_filter.setFixedWidth(100)
        btn_clear_filter.clicked.connect(lambda: self.search.clear())
        toolbar.addWidget(btn_clear_filter)

        btn_clear_chat = QPushButton("Clear chat")
        btn_clear_chat.setFixedWidth(90)
        btn_clear_chat.clicked.connect(self.clear_chat)
        toolbar.addWidget(btn_clear_chat)
        layout.addLayout(toolbar)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("Waiting for channel traffic…")
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

        ts = datetime.now()
        channel = packet.get("channel_hint", "") or ""
        entry = {
            "timestamp": ts.isoformat(timespec="seconds"),
            "from_node": sender,
            "message": msg,
            "channel": channel,
            "snr": packet.get("snr"),
            "rssi": packet.get("rssi"),
        }
        self.history.append(entry)
        self._append_html(entry)

    def _append_html(self, entry: dict) -> None:
        if self._filter:
            blob = f"{entry['from_node']} {entry['message']} {entry['channel']}".lower()
            if self._filter not in blob:
                return

        ts_str = entry["timestamp"][11:19] if "T" in entry["timestamp"] else entry["timestamp"]
        is_self = "(YOU)" in str(entry["from_node"])
        colour = "#00FF66" if is_self else "#C5D0DE"
        ch = entry.get("channel") or ""
        ch_badge = f' <span style="color:#5A6A7A">[{ch}]</span>' if ch else ""
        rf = ""
        if entry.get("snr") is not None:
            rf = f' <span style="color:#4A90D9">SNR {entry["snr"]:.1f}</span>'
        html = (
            f'<span style="color:#5A6A7A">[{ts_str}]</span> '
            f'<span style="color:{colour};font-weight:bold">{entry["from_node"]}</span>'
            f"{ch_badge}{rf}: "
            f'<span style="color:#E8EEF5">{entry["message"]}</span>'
        )
        self.chat_display.append(html)

    def _on_filter(self, text: str) -> None:
        self._filter = text.strip().lower()
        self.chat_display.clear()
        for entry in self.history:
            self._append_html(entry)

    def clear_chat(self) -> None:
        self.history.clear()
        self.chat_display.clear()

    def get_history(self) -> list[dict[str, Any]]:
        return list(self.history)
