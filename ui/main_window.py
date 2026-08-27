import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QLabel
from PySide6.QtCore import Qt
from ui.widgets.node_list import NodeListWidget
from ui.widgets.chat import ChatWidget
 
from ui.widgets.map_view import MapWidget

logger = logging.getLogger(__name__)

class XmeshMainWindow(QMainWindow):
    def __init__(self, signals=None, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.active_nodes = set()
        self.message_count = 0

        self.setWindowTitle("XMESH")
        self.resize(1100, 650)

        # Central Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Sidebar Navigation
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar)
        
        self.btn_nodedb = QLabel("📡  NODE DB")
        self.btn_chat = QLabel("💬  LIVE CHAT")
        self.btn_telemetry = QLabel("🗺️  TELEMETRY")
        
        for btn in [self.btn_nodedb, self.btn_chat, self.btn_telemetry]:
            btn.setCursor(Qt.PointingHandCursor)
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # Right Panel
        right_panel = QVBoxLayout()

        # Stats Header
        stats_layout = QHBoxLayout()
        self.lbl_nodes_cnt = QLabel("ACTIVE NODES\n0")
        self.lbl_msg_cnt = QLabel("MESSAGES CAPTURED\n0")
        stats_layout.addWidget(self.lbl_nodes_cnt)
        stats_layout.addWidget(self.lbl_msg_cnt)
        stats_layout.addStretch()
        
        right_panel.addLayout(stats_layout)

        # Stacked Screens
        self.stack = QStackedWidget()
        self.node_widget = NodeListWidget()
        self.chat_widget = ChatWidget(signals=self.signals)
        self.map_widget = MapWidget()

        self.stack.addWidget(self.node_widget)
        self.stack.addWidget(self.chat_widget)
        self.stack.addWidget(self.map_widget)

        right_panel.addWidget(self.stack)
        main_layout.addLayout(right_panel)

        # Navigation Click Handlers
        self.btn_nodedb.mousePressEvent = lambda e: self.stack.setCurrentIndex(0)
        self.btn_chat.mousePressEvent = lambda e: self.stack.setCurrentIndex(1)
        self.btn_telemetry.mousePressEvent = lambda e: self.stack.setCurrentIndex(2)

        # Connect Signals
        if self.signals:
            self.signals.node_updated.connect(self.on_node_updated)
            self.signals.message_received.connect(self.on_message_received)

    def on_node_updated(self, packet):
        node_id = packet.get("from_node")
        if node_id and node_id != "UNKNOWN":
            self.active_nodes.add(node_id)
            self.lbl_nodes_cnt.setText(f"ACTIVE NODES\n{len(self.active_nodes)}")
            self.node_widget.update_node(packet)

    def on_message_received(self, packet):
        self.message_count += 1
        self.lbl_msg_cnt.setText(f"MESSAGES CAPTURED\n{self.message_count}")