"""Production-grade Meshtastic MQTT client – multi-topic, TLS, reconnect, signal bus."""

from __future__ import annotations

import logging
import random
import ssl
from typing import Optional, Sequence

import paho.mqtt.client as mqtt
from meshtastic import mesh_pb2, mqtt_pb2, portnums_pb2

from core.protobuf_decoder import ProtobufDecoder
from core.signals import MeshSignals

logger = logging.getLogger(__name__)


class MeshtasticMQTTClient:
    """Connects to a Meshtastic MQTT broker with multi-topic and multi-PSK support."""

    def __init__(
        self,
        broker: str,
        port: int,
        topics: Sequence[str],
        username: str = "meshdev",
        password: str = "large4cats",
        use_tls: bool = False,
        channel_key: str = "AQ==",
        extra_keys: Optional[list[str]] = None,
        signals: Optional[MeshSignals] = None,
    ) -> None:
        self.broker = broker
        self.port = port
        self.topics = list(topics) if topics else ["msh/+/2/c/LongFast/#"]
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.signals = signals

        self.my_node_num = random.randint(0x10000000, 0x7FFFFFFF)
        self.my_node_hex = f"!{self.my_node_num:08x}"
        self.packet_count = 0

        client_id = f"xmesh_{self.my_node_hex[1:]}"
        try:
            self.client = mqtt.Client(
                client_id=client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            )
        except (AttributeError, TypeError):
            self.client = mqtt.Client(client_id=client_id)

        if username and password:
            self.client.username_pw_set(username, password)

        self.decoder = ProtobufDecoder(
            channel_key_base64=channel_key,
            extra_keys_base64=extra_keys,
        )

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        if self.signals:
            self.signals.send_message_requested.connect(self.send_text_message)

    def _log(self, level: str, msg: str) -> None:
        getattr(logger, level.lower(), logger.info)(msg)
        if self.signals:
            self.signals.log_message.emit(level.upper(), msg)

    def connect(self) -> None:
        self._log(
            "INFO",
            f"Connecting to {self.broker}:{self.port} (TLS={self.use_tls}, topics={len(self.topics)})…",
        )
        try:
            if self.use_tls:
                self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
                self.client.tls_insecure_set(False)
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as exc:
            self._log("ERROR", f"Connection failed: {exc}")
            if self.signals:
                self.signals.connection_status.emit(False, f"Connection failed: {exc}")

    def disconnect(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def send_text_message(self, text: str) -> None:
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
            self._log("ERROR", "Encryption failed – message not sent")
            return

        mesh_packet = mesh_pb2.MeshPacket()
        setattr(mesh_packet, "from", self.my_node_num)
        mesh_packet.to = 0xFFFFFFFF
        mesh_packet.id = packet_id
        mesh_packet.encrypted = encrypted
        mesh_packet.channel = 0
        mesh_packet.hop_limit = 3

        envelope = mqtt_pb2.ServiceEnvelope()
        envelope.packet.CopyFrom(mesh_packet)
        envelope.channel_id = "LongFast"
        envelope.gateway_id = self.my_node_hex

        pub_topic = f"msh/EU_868/2/c/LongFast/{self.my_node_hex}"
        self.client.publish(pub_topic, envelope.SerializeToString(), qos=0)
        self._log("INFO", f"📤 Sent [{pub_topic}]: {text}")

        if self.signals:
            self.signals.message_received.emit(
                {
                    "type": "TEXT_MESSAGE",
                    "from_node": f"{self.my_node_hex} (YOU)",
                    "data": text,
                    "channel_hint": "LongFast",
                }
            )

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        rc = reason_code if isinstance(reason_code, int) else getattr(reason_code, "value", reason_code)
        if rc == 0:
            for t in self.topics:
                client.subscribe(t, qos=0)
                self._log("INFO", f"Subscribed → {t}")
            if self.signals:
                self.signals.connection_status.emit(
                    True, f"Connected to {self.broker} ({len(self.topics)} topic(s))"
                )
        else:
            self._log("ERROR", f"MQTT connect failed (rc={rc})")
            if self.signals:
                self.signals.connection_status.emit(False, f"Connect failed (rc={rc})")

    def _on_message(self, client, userdata, msg) -> None:
        try:
            packet = self.decoder.decode_mqtt_payload(msg.topic, msg.payload)
            if not packet:
                return

            self.packet_count += 1
            packet_type = str(packet.get("type", "")).upper()
            from_node = packet.get("from_node", "UNKNOWN")

            if not self.signals:
                return

            if from_node != "UNKNOWN":
                self.signals.node_updated.emit(packet)

            if "TEXT" in packet_type:
                self.signals.message_received.emit(packet)
            elif "POSITION" in packet_type:
                self.signals.position_updated.emit(packet)
            elif "TELEMETRY" in packet_type:
                self.signals.node_updated.emit(packet)

        except Exception as exc:
            self._log("ERROR", f"Packet error: {exc}")

    def _on_disconnect(self, client, userdata, *args) -> None:
        rc = 0
        if args:
            rc = args[0] if isinstance(args[0], int) else getattr(args[0], "value", 0)
        if rc != 0:
            self._log("WARN", f"Unexpected disconnect (rc={rc}) – auto-reconnect active")
            if self.signals:
                self.signals.connection_status.emit(False, "Disconnected – reconnecting…")
        else:
            if self.signals:
                self.signals.connection_status.emit(False, "Disconnected")
