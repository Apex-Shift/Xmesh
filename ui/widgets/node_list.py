"""Dynamic node database with search, RF metrics and clipboard actions."""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.node import Node


class NodeListWidget(QWidget):
    COLUMNS = (
        "Node ID",
        "Short",
        "Long Name",
        "Hardware",
        "SNR",
        "RSSI",
        "Batt",
        "Channel",
        "Last Seen",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.nodes: dict[str, Node] = {}
        self._filter = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Filter nodes (id, name, hw, channel)…")
        self.search.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search)

        btn_clear = QPushButton("Clear filter")
        btn_clear.setFixedWidth(100)
        btn_clear.clicked.connect(lambda: self.search.clear())
        toolbar.addWidget(btn_clear)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.table)

    def update_node(self, packet: dict) -> None:
        node_id = packet.get("from_node")
        if not node_id or node_id == "UNKNOWN":
            return

        data = packet.get("data") if isinstance(packet.get("data"), dict) else {}

        if node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id=node_id)

        node = self.nodes[node_id]
        node.update_info(
            short_name=data.get("short_name"),
            long_name=data.get("long_name"),
            hw_model=data.get("hw_model"),
        )
        node.update_rf(
            snr=packet.get("snr"),
            rssi=packet.get("rssi"),
            hop_start=packet.get("hop_start"),
        )
        if "battery_level" in data or "voltage" in data:
            node.update_telemetry(
                battery_level=data.get("battery_level"),
                voltage=data.get("voltage"),
            )
        ch = packet.get("channel_hint")
        if ch and ch != "unknown":
            node.channel = ch

        # Position may also arrive via node_updated path
        if packet.get("type") == "POSITION" and data:
            lat, lon = data.get("latitude"), data.get("longitude")
            if lat is not None and lon is not None:
                node.update_position(float(lat), float(lon), float(data.get("altitude") or 0))

        self._refresh_visible()

    def _row_values(self, node: Node) -> list[str]:
        snr = f"{node.snr:.1f}" if node.snr is not None else ""
        rssi = str(node.rssi) if node.rssi is not None else ""
        return [
            node.node_id,
            node.short_name,
            node.long_name,
            node.hw_model,
            snr,
            rssi,
            node.battery_str(),
            node.channel,
            node.last_seen.strftime("%H:%M:%S"),
        ]

    def _matches_filter(self, node: Node) -> bool:
        if not self._filter:
            return True
        blob = " ".join(
            [
                node.node_id,
                node.short_name,
                node.long_name,
                node.hw_model,
                node.channel,
            ]
        ).lower()
        return self._filter in blob

    def _refresh_visible(self) -> None:
        # Rebuild table from filtered nodes (simple & reliable)
        visible = [n for n in self.nodes.values() if self._matches_filter(n)]
        visible.sort(key=lambda n: n.last_seen, reverse=True)

        self.table.setRowCount(0)
        for node in visible:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate(self._row_values(node)):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

    def _apply_filter(self, text: str) -> None:
        self._filter = text.strip().lower()
        self._refresh_visible()

    def _context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        node_id_item = self.table.item(row, 0)
        if not node_id_item:
            return
        node_id = node_id_item.text()
        node = self.nodes.get(node_id)
        if not node:
            return

        menu = QMenu(self)
        act_copy_id = QAction(f"Copy Node ID ({node_id})", self)
        act_copy_id.triggered.connect(lambda: QGuiApplication.clipboard().setText(node_id))
        menu.addAction(act_copy_id)

        if node.has_position():
            coords = f"{node.latitude:.6f}, {node.longitude:.6f}"
            act_copy_pos = QAction(f"Copy coordinates ({coords})", self)
            act_copy_pos.triggered.connect(lambda: QGuiApplication.clipboard().setText(coords))
            menu.addAction(act_copy_pos)

        act_copy_name = QAction("Copy display name", self)
        act_copy_name.triggered.connect(
            lambda: QGuiApplication.clipboard().setText(node.display_name())
        )
        menu.addAction(act_copy_name)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def node_count(self) -> int:
        return len(self.nodes)

    def export_rows(self) -> list[dict[str, Any]]:
        rows = []
        for node in self.nodes.values():
            rows.append(
                {
                    "node_id": node.node_id,
                    "short_name": node.short_name,
                    "long_name": node.long_name,
                    "hw_model": node.hw_model,
                    "snr": node.snr,
                    "rssi": node.rssi,
                    "battery": node.battery_str(),
                    "voltage": node.voltage,
                    "channel": node.channel,
                    "last_seen": node.last_seen.isoformat(timespec="seconds"),
                    "latitude": node.latitude,
                    "longitude": node.longitude,
                    "altitude": node.altitude,
                }
            )
        return rows
