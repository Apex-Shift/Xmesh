"""Production-grade Meshtastic MQTT client with TLS, reconnect and signal bus."""

from __future__ import annotations

import logging
import random
import ssl
from typing import Optional

import paho.mqtt.client as mqtt
from meshtastic import mesh_pb2, mqtt_pb2, portnums_pb2

from core.protobuf_decoder import ProtobufDecoder
from core.signals import MeshSignals

logger = logging.getLogger(__name__)


class MeshtasticMQTTClient:
    """Connects to a public or private Meshtastic MQTT broker and exchanges packets."""

    def __init__(
        self,
        broker: str,
        port: int,
        topic: str,
        username: str = "meshdev",
        password: str = "large4cats",
        use_tls: bool = False,
        channel_key: str = "AQ==",
        signals: Optional[MeshSignals] = None,
    ) -> None:
        self.broker = broker
        self.port = port
        self.topic = topic
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.signals = signals

        # Synthetic node identity for outbound messages
        self.my_node_num = random.randint(0x10000000, 0x7FFFFFFF)
        self.my_node_hex = f"!{self.my_node_num:08x}"

        client_id = f"xmesh_{self.my_node_hex[1:]}"
        # Callback API v2 (paho-mqtt >= 2.0) or classic
        try:
            self.client = mqtt.Client(
                client_id=client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            )
        except (AttributeError, TypeError):
            self.client = mqtt.Client(client_id=client_id)

        if username and password:
            self.client.username_pw_set(username, password)

        self.decoder = ProtobufDecoder(channel_key_base64=channel_key)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        if self.signals:
            self.signals.send_message_requested.connect(self.send_text_message)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def connect(self) -> None:
        logger.info("Connecting to %s:%s (TLS=%s)…", self.broker, self.port, self.use_tls)
        try:
            if self.use_tls:
                self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
                self.client.tls_insecure_set(False)

            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as exc:
            logger.error("Connection failed: %s", exc)
            if self.signals:
                self.signals.connection_status.emit(False, f"Connection failed: {exc}")

    def disconnect(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def send_text_message(self, text: str) -> None:
        """Encrypt and publish a TEXT_MESSAGE_APP packet to the mesh."""
        if not text or not text.strip():
            return

        text = text.strip()
        packet_id = random.randint(1, 0xFFFFFFFF)

        data_struct = mesh_pb2.Data()
        data_struct.portnum = portnums_pb2.PortNum.TEXT_MESSAGE_APP
        data_struct.payload = text.encode("utf-8")

        encrypted = self.decoder.encrypt_payload(
            packet_id, self.my_node_num, data_struct.SerializeToString()
        )
        if not encrypted:
            logger.error("Encryption produced empty payload – message not sent")
            return

        mesh_packet = mesh_pb2.MeshPacket()
        setattr(mesh_packet, "from", self.my_node_num)
        mesh_packet.to = 0xFFFFFFFF  # broadcast
        mesh_packet.id = packet_id
        mesh_packet.encrypted = encrypted
        mesh_packet.channel = 0
        mesh_packet.hop_limit = 3

        envelope = mqtt_pb2.ServiceEnvelope()
        envelope.packet.CopyFrom(mesh_packet)
        envelope.channel_id = "LongFast"
        envelope.gateway_id = self.my_node_hex

        # Publish under a plausible regional topic so gateways accept it
        pub_topic = f"msh/EU_868/2/c/LongFast/{self.my_node_hex}"
        result = self.client.publish(pub_topic, envelope.SerializeToString(), qos=0)
        logger.info("📤 Published to [%s]: %s (mid=%s)", pub_topic, text, result.mid)

        if self.signals:
            self.signals.message_received.emit(
                {
                    "type": "TEXT_MESSAGE",
                    "from_node": f"{self.my_node_hex} (YOU)",
                    "data": text,
                }
            )

    # ------------------------------------------------------------------ #
    # MQTT callbacks
    # ------------------------------------------------------------------ #
    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        # Compatible with both paho v1 (rc) and v2 (reason_code)
        rc = reason_code if isinstance(reason_code, int) else getattr(reason_code, "value", reason_code)
        if rc == 0:
            logger.info("✅ Connected to broker – subscribing to %s", self.topic)
            client.subscribe(self.topic, qos=0)
            if self.signals:
                self.signals.connection_status.emit(True, f"Connected to {self.broker}")
        else:
            logger.error("MQTT connect failed (rc=%s)", rc)
            if self.signals:
                self.signals.connection_status.emit(False, f"Connect failed (rc={rc})")

    def _on_message(self, client, userdata, msg) -> None:
        try:
            packet = self.decoder.decode_mqtt_payload(msg.topic, msg.payload)
            if not packet:
                return

            packet_type = str(packet.get("type", "")).upper()
            from_node = packet.get("from_node", "UNKNOWN")

            if not self.signals:
                return

            # Always feed node identity when available
            if from_node != "UNKNOWN":
                self.signals.node_updated.emit(packet)

            if "TEXT" in packet_type:
                self.signals.message_received.emit(packet)
            elif "POSITION" in packet_type:
                self.signals.position_updated.emit(packet)

        except Exception as exc:
            logger.error("Error processing packet: %s", exc, exc_info=True)

    def _on_disconnect(self, client, userdata, *args) -> None:
        # paho v1: (client, userdata, rc)
        # paho v2: (client, userdata, flags, reason_code, properties)
        rc = 0
        if args:
            rc = args[0] if isinstance(args[0], int) else getattr(args[0], "value", 0)

        if rc != 0:
            logger.warning("Unexpected disconnect (rc=%s) – paho will auto-reconnect", rc)
            if self.signals:
                self.signals.connection_status.emit(False, "Disconnected – reconnecting…")
        else:
            if self.signals:
                self.signals.connection_status.emit(False, "Disconnected")
