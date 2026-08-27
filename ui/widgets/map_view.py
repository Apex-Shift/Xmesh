"""Telemetry / position view – tabular live positions (map-ready data)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.node import Node


class MapWidget(QWidget):
    """Displays last known GPS positions of mesh nodes."""

    COLUMNS = ("Node", "Latitude", "Longitude", "Altitude (m)", "Last Update")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.nodes: dict[str, Node] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("🗺️  LIVE POSITION TELEMETRY")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #00FF66; font-size: 15px; font-weight: bold; padding: 6px;"
        )
        layout.addWidget(title)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        hint = QLabel(
            "Positions are extracted from POSITION_APP packets. "
            "Integrate a mapping library (folium / pyqt-leaflet) for geographic rendering."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #5A6A7A; font-size: 11px;")
        layout.addWidget(hint)

    def update_position(self, packet: dict) -> None:
        node_id = packet.get("from_node")
        data = packet.get("data", {})
        if not node_id or not isinstance(data, dict):
            return

        lat = data.get("latitude")
        lon = data.get("longitude")
        if lat is None or lon is None:
            return

        if node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id=node_id)

        node = self.nodes[node_id]
        node.update_position(lat, lon, data.get("altitude", 0))

        row = self._find_row(node_id)
        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)

        values = [
            node_id,
            f"{lat:.6f}",
            f"{lon:.6f}",
            str(data.get("altitude", 0)),
            node.last_seen.strftime("%H:%M:%S"),
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, col, item)

    def _find_row(self, node_id: str) -> int | None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == node_id:
                return row
        return None
