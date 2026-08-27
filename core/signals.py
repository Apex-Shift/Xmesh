from PySide6.QtCore import QObject, Signal

class MeshSignals(QObject):
    message_received = Signal(dict)
    node_updated = Signal(dict)
    position_updated = Signal(dict)
    send_message_requested = Signal(str)  # Outgoing text signal