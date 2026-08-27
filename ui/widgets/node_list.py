"""Dynamic node database table."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.node import Node


class NodeListWidget(QWidget):
    COLUMNS = ("Node ID", "Short", "Long Name", "Hardware", "Last Seen")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.nodes: dict[str, Node] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def update_node(self, packet: dict) -> None:
        node_id = packet.get("from_node")
        data = packet.get("data", {})
        if not node_id or node_id == "UNKNOWN":
            return

        if not isinstance(data, dict):
            data = {}

        if node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id=node_id)

        node = self.nodes[node_id]
        node.update_info(
            short_name=data.get("short_name"),
            long_name=data.get("long_name"),
            hw_model=data.get("hw_model"),
        )

        self._refresh_row(node)

    def _refresh_row(self, node: Node) -> None:
        row = self._find_row(node.node_id)
        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)

        values = [
            node.node_id,
            node.short_name,
            node.long_name,
            node.hw_model,
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

    def node_count(self) -> int:
        return len(self.nodes)
