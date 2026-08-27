"""Main application window – tactical dark UI for Xmesh."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStatusBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.chat import ChatWidget
from ui.widgets.map_view import MapWidget
from ui.widgets.node_list import NodeListWidget

logger = logging.getLogger(__name__)


class XmeshMainWindow(QMainWindow):
    def __init__(self, signals=None, parent=None) -> None:
        super().__init__(parent)
        self.signals = signals
        self.active_nodes: set[str] = set()
        self.message_count = 0

        self.setWindowTitle("XMESH – Expert Meshtastic Monitor")
        self.resize(1200, 720)
        self.setMinimumSize(900, 560)

        self._build_ui()
        self._wire_signals()

    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ----- Sidebar -----
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(190)
        for label in ("📡  NODE DB", "💬  LIVE CHAT", "🗺️  TELEMETRY"):
            item = QListWidgetItem(label)
            item.setTextAlignment(Qt.AlignVCenter)
            self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._on_nav)
        root.addWidget(self.sidebar)

        # ----- Right panel -----
        right = QVBoxLayout()
        right.setContentsMargins(12, 12, 12, 12)
        right.setSpacing(10)

        # Stats cards
        stats = QHBoxLayout()
        self.lbl_nodes = self._make_stat_card("ACTIVE NODES", "0")
        self.lbl_msgs = self._make_stat_card("MESSAGES CAPTURED", "0")
        self.lbl_status = self._make_stat_card("CONNECTION", "DISCONNECTED")
        stats.addWidget(self.lbl_nodes)
        stats.addWidget(self.lbl_msgs)
        stats.addWidget(self.lbl_status)
        stats.addStretch()
        right.addLayout(stats)

        # Stacked pages
        self.stack = QStackedWidget()
        self.node_widget = NodeListWidget()
        self.chat_widget = ChatWidget(signals=self.signals)
        self.map_widget = MapWidget()

        self.stack.addWidget(self.node_widget)
        self.stack.addWidget(self.chat_widget)
        self.stack.addWidget(self.map_widget)
        right.addWidget(self.stack)

        root.addLayout(right, stretch=1)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready – waiting for MQTT connection…")

    def _make_stat_card(self, title: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("StatCard")
        frame.setFixedHeight(64)
        frame.setMinimumWidth(160)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(2)

        t = QLabel(title)
        t.setStyleSheet("color: #5A6A7A; font-size: 10px; font-weight: bold;")
        v = QLabel(value)
        v.setObjectName("StatValue")
        v.setStyleSheet("color: #00FF66; font-size: 18px; font-weight: bold;")
        lay.addWidget(t)
        lay.addWidget(v)
        frame.value_label = v  # type: ignore[attr-defined]
        return frame

    # ------------------------------------------------------------------ #
    def _wire_signals(self) -> None:
        if not self.signals:
            return
        self.signals.node_updated.connect(self.on_node_updated)
        self.signals.message_received.connect(self.on_message_received)
        self.signals.position_updated.connect(self.on_position_updated)
        self.signals.connection_status.connect(self.on_connection_status)

    def _on_nav(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #
    def on_node_updated(self, packet: dict) -> None:
        node_id = packet.get("from_node")
        if node_id and node_id != "UNKNOWN":
            self.active_nodes.add(node_id)
            self.lbl_nodes.value_label.setText(str(len(self.active_nodes)))
            self.node_widget.update_node(packet)

    def on_message_received(self, packet: dict) -> None:
        self.message_count += 1
        self.lbl_msgs.value_label.setText(str(self.message_count))
        # ChatWidget already listens to the same signal

    def on_position_updated(self, packet: dict) -> None:
        self.map_widget.update_position(packet)
        # Also keep the node DB fresh
        self.on_node_updated(packet)

    def on_connection_status(self, connected: bool, message: str) -> None:
        colour = "#00FF66" if connected else "#FF5555"
        text = "ONLINE" if connected else "OFFLINE"
        self.lbl_status.value_label.setText(text)
        self.lbl_status.value_label.setStyleSheet(
            f"color: {colour}; font-size: 18px; font-weight: bold;"
        )
        self.status.showMessage(message)
