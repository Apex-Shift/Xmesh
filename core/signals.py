"""Qt signal bus used to decouple the MQTT layer from the GUI."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class MeshSignals(QObject):
    """Central signal hub for mesh events.

    Signals
    -------
    message_received : dict
        Emitted when a TEXT_MESSAGE packet is decoded.
    node_updated : dict
        Emitted on NODEINFO or any packet that carries node identity.
    position_updated : dict
        Emitted when a POSITION_APP packet is received.
    send_message_requested : str
        Emitted by the UI when the user wants to broadcast text.
    connection_status : bool, str
        Emitted on connect / disconnect (connected flag + human message).
    """

    message_received = Signal(dict)
    node_updated = Signal(dict)
    position_updated = Signal(dict)
    send_message_requested = Signal(str)
    connection_status = Signal(bool, str)
