"""Main application window – tactical dark UI for Xmesh v2.2."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QStackedWidget,
    QTextEdit,
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
        self.packet_count = 0

        self.setWindowTitle("XMESH – Expert Meshtastic Monitor v2.2")
        self.resize(1280, 780)
        self.setMinimumSize(960, 600)

        self._build_menu()
        self._build_ui()
        self._wire_signals()

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        act_export_nodes = QAction("Export Nodes to CSV…", self)
        act_export_nodes.setShortcut(QKeySequence("Ctrl+E"))
        act_export_nodes.triggered.connect(self.export_nodes_csv)
        file_menu.addAction(act_export_nodes)

        act_export_msgs = QAction("Export Messages to CSV…", self)
        act_export_msgs.setShortcut(QKeySequence("Ctrl+M"))
        act_export_msgs.triggered.connect(self.export_messages_csv)
        file_menu.addAction(act_export_msgs)

        act_export_pos = QAction("Export Positions to CSV…", self)
        act_export_pos.triggered.connect(self.export_positions_csv)
        file_menu.addAction(act_export_pos)
        file_menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        view_menu = menubar.addMenu("&View")
        act_map = QAction("Open Interactive Map", self)
        act_map.setShortcut(QKeySequence("Ctrl+Shift+M"))
        act_map.triggered.connect(lambda: self.map_widget.open_interactive_map())
        view_menu.addAction(act_map)

        act_logs = QAction("Show / Hide Logs", self)
        act_logs.setShortcut(QKeySequence("Ctrl+L"))
        act_logs.triggered.connect(self._toggle_logs)
        view_menu.addAction(act_logs)

        help_menu = menubar.addMenu("&Help")
        act_about = QAction("About XMESH", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(190)
        for label in ("📡  NODE DB", "💬  LIVE CHAT", "🗺️  TELEMETRY", "📋  LOGS"):
            item = QListWidgetItem(label)
            item.setTextAlignment(Qt.AlignVCenter)
            self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._on_nav)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(12, 12, 12, 12)
        right.setSpacing(10)

        stats = QHBoxLayout()
        self.lbl_nodes = self._make_stat_card("ACTIVE NODES", "0")
        self.lbl_msgs = self._make_stat_card("MESSAGES", "0")
        self.lbl_pkts = self._make_stat_card("PACKETS", "0")
        self.lbl_status = self._make_stat_card("CONNECTION", "DISCONNECTED")
        for w in (self.lbl_nodes, self.lbl_msgs, self.lbl_pkts, self.lbl_status):
            stats.addWidget(w)
        stats.addStretch()
        right.addLayout(stats)

        self.stack = QStackedWidget()
        self.node_widget = NodeListWidget()
        self.chat_widget = ChatWidget(signals=self.signals)
        self.map_widget = MapWidget()
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setPlaceholderText("Application log…")
        self.log_widget.setObjectName("LogView")

        self.stack.addWidget(self.node_widget)
        self.stack.addWidget(self.chat_widget)
        self.stack.addWidget(self.map_widget)
        self.stack.addWidget(self.log_widget)
        right.addWidget(self.stack)

        root.addLayout(right, stretch=1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready – waiting for MQTT connection…")

    def _make_stat_card(self, title: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("StatCard")
        frame.setFixedHeight(64)
        frame.setMinimumWidth(140)
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

    def _wire_signals(self) -> None:
        if not self.signals:
            return
        self.signals.node_updated.connect(self.on_node_updated)
        self.signals.message_received.connect(self.on_message_received)
        self.signals.position_updated.connect(self.on_position_updated)
        self.signals.connection_status.connect(self.on_connection_status)
        self.signals.log_message.connect(self.on_log_message)

    def _on_nav(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def _toggle_logs(self) -> None:
        self.sidebar.setCurrentRow(3)

    # ------------------------------------------------------------------ #
    def on_node_updated(self, packet: dict) -> None:
        self.packet_count += 1
        self.lbl_pkts.value_label.setText(str(self.packet_count))
        node_id = packet.get("from_node")
        if node_id and node_id != "UNKNOWN":
            self.active_nodes.add(node_id)
            self.lbl_nodes.value_label.setText(str(len(self.active_nodes)))
            self.node_widget.update_node(packet)

    def on_message_received(self, packet: dict) -> None:
        self.message_count += 1
        self.lbl_msgs.value_label.setText(str(self.message_count))

    def on_position_updated(self, packet: dict) -> None:
        self.map_widget.update_position(packet)
        self.on_node_updated(packet)

    def on_connection_status(self, connected: bool, message: str) -> None:
        colour = "#00FF66" if connected else "#FF5555"
        text = "ONLINE" if connected else "OFFLINE"
        self.lbl_status.value_label.setText(text)
        self.lbl_status.value_label.setStyleSheet(
            f"color: {colour}; font-size: 18px; font-weight: bold;"
        )
        self.status.showMessage(message)

    def on_log_message(self, level: str, text: str) -> None:
        colours = {
            "INFO": "#7A8B9E",
            "WARN": "#FFAA33",
            "ERROR": "#FF5555",
        }
        c = colours.get(level, "#7A8B9E")
        ts = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:#5A6A7A">[{ts}]</span> <span style="color:{c}">[{level}]</span> {text}'
        self.log_widget.append(html)
        self.log_widget.moveCursor(QTextCursor.End)

    # ------------------------------------------------------------------ #
    def _save_csv(self, default_name: str, fieldnames: list[str], rows: list[dict]) -> None:
        if not rows:
            QMessageBox.information(self, "Export", "No data to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", str(Path.home() / default_name), "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            self.status.showMessage(f"Exported {len(rows)} row(s) → {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def export_nodes_csv(self) -> None:
        rows = self.node_widget.export_rows()
        fields = [
            "node_id", "short_name", "long_name", "hw_model",
            "snr", "rssi", "battery", "voltage", "channel",
            "last_seen", "latitude", "longitude", "altitude",
        ]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_csv(f"xmesh_nodes_{stamp}.csv", fields, rows)

    def export_messages_csv(self) -> None:
        rows = self.chat_widget.get_history()
        fields = ["timestamp", "from_node", "message", "channel", "snr", "rssi"]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_csv(f"xmesh_messages_{stamp}.csv", fields, rows)

    def export_positions_csv(self) -> None:
        rows = self.map_widget.export_rows()
        fields = ["node_id", "short_name", "latitude", "longitude", "altitude", "last_seen"]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_csv(f"xmesh_positions_{stamp}.csv", fields, rows)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About XMESH",
            "<h3>XMESH Expert v2.2</h3>"
            "<p>Meshtastic MQTT monitor</p>"
            "<p>AES-128-CTR · Multi-channel · SNR/RSSI · Telemetry<br>"
            "Interactive map · CSV export · Search · Logs</p>"
            "<p>MIT License</p>",
        )
