"""Position telemetry table + one-click interactive Leaflet map."""

from __future__ import annotations

import logging
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.node import Node

logger = logging.getLogger(__name__)

try:
    import folium
    from folium.plugins import MarkerCluster

    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False


class MapWidget(QWidget):
    COLUMNS = ("Node", "Latitude", "Longitude", "Altitude (m)", "Last Update")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.nodes: dict[str, Node] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        self.title = QLabel("🗺️  LIVE POSITION TELEMETRY  ·  0 markers")
        self.title.setStyleSheet(
            "color: #00FF66; font-size: 15px; font-weight: bold; padding: 6px;"
        )
        header.addWidget(self.title)
        header.addStretch()

        self.btn_map = QPushButton("🌍 Open Interactive Map")
        self.btn_map.setToolTip("Leaflet map with clustered markers (opens in browser)")
        self.btn_map.clicked.connect(self.open_interactive_map)
        self.btn_map.setEnabled(HAS_FOLIUM)
        header.addWidget(self.btn_map)

        if not HAS_FOLIUM:
            warn = QLabel("(pip install folium)")
            warn.setStyleSheet("color: #FF8855; font-size: 11px;")
            header.addWidget(warn)

        layout.addLayout(header)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        hint = QLabel(
            "Positions from POSITION_APP packets. "
            "Click « Open Interactive Map » for a zoomable dark Leaflet map."
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
        if abs(float(lat)) < 1e-5 and abs(float(lon)) < 1e-5:
            return

        if node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id=node_id)

        node = self.nodes[node_id]
        node.update_position(float(lat), float(lon), float(data.get("altitude") or 0))

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

        count = sum(1 for n in self.nodes.values() if n.has_position())
        self.title.setText(f"🗺️  LIVE POSITION TELEMETRY  ·  {count} marker(s)")

    def _find_row(self, node_id: str) -> Optional[int]:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == node_id:
                return row
        return None

    def open_interactive_map(self) -> None:
        if not HAS_FOLIUM:
            return

        positioned = [n for n in self.nodes.values() if n.has_position()]
        if not positioned:
            m = folium.Map(location=[48.85, 2.35], zoom_start=5, tiles="CartoDB dark_matter")
            folium.Marker(
                [48.85, 2.35], popup="No positions yet – waiting for GPS packets"
            ).add_to(m)
        else:
            avg_lat = sum(n.latitude for n in positioned) / len(positioned)  # type: ignore
            avg_lon = sum(n.longitude for n in positioned) / len(positioned)  # type: ignore
            m = folium.Map(
                location=[avg_lat, avg_lon],
                zoom_start=6,
                tiles="CartoDB dark_matter",
            )
            cluster = MarkerCluster().add_to(m)
            for node in positioned:
                popup = (
                    f"<b>{node.display_name()}</b><br>"
                    f"Lat: {node.latitude:.6f}<br>"
                    f"Lon: {node.longitude:.6f}<br>"
                    f"Alt: {node.altitude or 0} m<br>"
                    f"Seen: {node.last_seen.strftime('%H:%M:%S')}"
                )
                folium.Marker(
                    [node.latitude, node.longitude],
                    popup=folium.Popup(popup, max_width=280),
                    tooltip=node.short_name or node.node_id,
                    icon=folium.Icon(color="green", icon="broadcast-tower", prefix="fa"),
                ).add_to(cluster)

        out = Path(tempfile.gettempdir()) / "xmesh_live_map.html"
        m.save(str(out))
        logger.info("Map written to %s (%d markers)", out, len(positioned))
        webbrowser.open(out.as_uri())

    def export_rows(self) -> list[dict[str, Any]]:
        rows = []
        for node in self.nodes.values():
            if not node.has_position():
                continue
            rows.append(
                {
                    "node_id": node.node_id,
                    "short_name": node.short_name,
                    "latitude": node.latitude,
                    "longitude": node.longitude,
                    "altitude": node.altitude,
                    "last_seen": node.last_seen.isoformat(timespec="seconds"),
                }
            )
        return rows
