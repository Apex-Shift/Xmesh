"""Qt signal bus – decouples MQTT layer from the GUI."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class MeshSignals(QObject):
    """Central event bus for the whole application."""

    message_received = Signal(dict)       # TEXT_MESSAGE
    node_updated = Signal(dict)           # identity / telemetry / any node sighting
    position_updated = Signal(dict)       # POSITION_APP
    send_message_requested = Signal(str)  # UI → MQTT
    connection_status = Signal(bool, str) # online flag + human message
    log_message = Signal(str, str)        # level ("INFO"/"WARN"/"ERROR"), text
