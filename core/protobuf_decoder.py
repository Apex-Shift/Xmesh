"""AES-CTR encryption / decryption and Meshtastic protobuf decoding."""

from __future__ import annotations

import base64
import logging
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from meshtastic import mesh_pb2, mqtt_pb2, portnums_pb2

logger = logging.getLogger(__name__)

# Official Meshtastic default channel key (base64 "AQ==")
DEFAULT_KEY_BYTES = bytes(
    [
        0xD4,
        0xF1,
        0xBB,
        0x3A,
        0x20,
        0x29,
        0x07,
        0x59,
        0xF0,
        0xBC,
        0xFF,
        0xAB,
        0xCF,
        0x4E,
        0x69,
        0x01,
    ]
)


class ProtobufDecoder:
    """Decrypts and decodes Meshtastic ServiceEnvelope / MeshPacket payloads."""

    def __init__(self, channel_key_base64: str = "AQ==") -> None:
        self.key = self._resolve_key(channel_key_base64)

    @staticmethod
    def _resolve_key(key_b64: str) -> bytes:
        if key_b64 in ("AQ==", "", None):
            return DEFAULT_KEY_BYTES
        try:
            decoded = base64.b64decode(key_b64)
            return decoded.ljust(16, b"\x00")[:16]
        except Exception as exc:
            logger.warning("Invalid channel key, falling back to default: %s", exc)
            return DEFAULT_KEY_BYTES

    def _aes_ctr(self, packet_id: int, from_node: int, data: bytes, encrypt: bool) -> bytes:
        """AES-128-CTR with the classic Meshtastic IV = packet_id || from_node."""
        try:
            iv = packet_id.to_bytes(8, "little") + from_node.to_bytes(8, "little")
            cipher = Cipher(algorithms.AES(self.key), modes.CTR(iv), backend=default_backend())
            if encrypt:
                return cipher.encryptor().update(data) + cipher.encryptor().finalize()
            return cipher.decryptor().update(data) + cipher.decryptor().finalize()
        except Exception as exc:
            logger.error("AES-CTR %s failed: %s", "encrypt" if encrypt else "decrypt", exc)
            return b""

    def decrypt_payload(self, packet_id: int, from_node: int, encrypted_bytes: bytes) -> bytes:
        return self._aes_ctr(packet_id, from_node, encrypted_bytes, encrypt=False)

    def encrypt_payload(self, packet_id: int, from_node: int, plaintext_bytes: bytes) -> bytes:
        return self._aes_ctr(packet_id, from_node, plaintext_bytes, encrypt=True)

    def decode_mqtt_payload(self, topic: str, raw_payload: bytes) -> dict[str, Any]:
        """Parse an MQTT payload into a normalised dict."""
        result: dict[str, Any] = {
            "type": "UNKNOWN",
            "from_node": "UNKNOWN",
            "data": {},
            "topic": topic,
        }

        # Prefer node id from topic (.../!aabbccdd)
        parts = topic.split("/")
        if parts and parts[-1].startswith("!"):
            result["from_node"] = parts[-1]

        try:
            envelope = mqtt_pb2.ServiceEnvelope()
            envelope.ParseFromString(raw_payload)
            packet = envelope.packet

            from_node_val = getattr(packet, "from", 0) or getattr(packet, "from_node", 0)
            if from_node_val:
                result["from_node"] = f"!{from_node_val:08x}"

            if packet.HasField("encrypted") and packet.encrypted:
                plain = self.decrypt_payload(packet.id, from_node_val, packet.encrypted)
                if plain:
                    data_struct = mesh_pb2.Data()
                    data_struct.ParseFromString(plain)
                    return self._process_data_struct(data_struct, result)
            elif packet.HasField("decoded"):
                return self._process_data_struct(packet.decoded, result)

        except Exception as exc:
            logger.debug("Failed to decode MQTT payload: %s", exc)

        if result["from_node"] != "UNKNOWN" and result["type"] == "UNKNOWN":
            result["type"] = "NODE_INFO"

        return result

    def _process_data_struct(
        self, data_struct: mesh_pb2.Data, result: dict[str, Any]
    ) -> dict[str, Any]:
        portnum = data_struct.portnum

        if portnum == portnums_pb2.PortNum.TEXT_MESSAGE_APP:
            result["type"] = "TEXT_MESSAGE"
            result["data"] = data_struct.payload.decode("utf-8", errors="replace")

        elif portnum == portnums_pb2.PortNum.NODEINFO_APP:
            result["type"] = "NODE_INFO"
            try:
                user = mesh_pb2.User()
                user.ParseFromString(data_struct.payload)
                result["data"] = {
                    "short_name": user.short_name or "?",
                    "long_name": user.long_name or "?",
                    "hw_model": mesh_pb2.HardwareModel.Name(user.hw_model),
                }
            except Exception as exc:
                logger.debug("NODEINFO parse error: %s", exc)

        elif portnum == portnums_pb2.PortNum.POSITION_APP:
            result["type"] = "POSITION"
            try:
                pos = mesh_pb2.Position()
                pos.ParseFromString(data_struct.payload)
                result["data"] = {
                    "latitude": pos.latitude_i / 1e7 if pos.latitude_i else 0.0,
                    "longitude": pos.longitude_i / 1e7 if pos.longitude_i else 0.0,
                    "altitude": pos.altitude or 0,
                }
            except Exception as exc:
                logger.debug("POSITION parse error: %s", exc)

        else:
            # Keep the packet for node tracking even if we don't fully understand it
            result["type"] = f"PORTNUM_{portnum}"

        return result
