from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Slot

class NodeListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Node ID", "Short Name", "Long Name", "Hardware"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.table)

    @Slot(dict)
    def update_node(self, packet: dict):
        node_id = packet.get("from_node")
        data = packet.get("data", {})
        
        if not node_id or not isinstance(data, dict):
            return

        self.nodes[node_id] = data

        row_count = self.table.rowCount()
        existing_row = None
        for row in range(row_count):
            if self.table.item(row, 0) and self.table.item(row, 0).text() == node_id:
                existing_row = row
                break

        row = existing_row if existing_row is not None else row_count
        if existing_row is None:
            self.table.insertRow(row_count)

        self.table.setItem(row, 0, QTableWidgetItem(str(node_id)))
        self.table.setItem(row, 1, QTableWidgetItem(str(data.get("short_name", "N/A"))))
        self.table.setItem(row, 2, QTableWidgetItem(str(data.get("long_name", "N/A"))))
        self.table.setItem(row, 3, QTableWidgetItem(str(data.get("hw_model", "N/A"))))