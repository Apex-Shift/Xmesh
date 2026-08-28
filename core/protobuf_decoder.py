"""AES-CTR encryption / decryption and rich Meshtastic protobuf decoding."""

from __future__ import annotations

import base64
import logging
from typing import Any, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from meshtastic import mesh_pb2, mqtt_pb2, portnums_pb2

logger = logging.getLogger(__name__)

DEFAULT_KEY_BYTES = bytes(
    [
        0xD4, 0xF1, 0xBB, 0x3A, 0x20, 0x29, 0x07, 0x59,
        0xF0, 0xBC, 0xFF, 0xAB, 0xCF, 0x4E, 0x69, 0x01,
    ]
)


class ProtobufDecoder:
    """Decrypts and decodes Meshtastic packets with multi-PSK support.

    Extracts RF metrics (SNR, RSSI, hops) and common app payloads
    (text, nodeinfo, position, device telemetry).
    """

    def __init__(
        self,
        channel_key_base64: str = "AQ==",
        extra_keys_base64: Optional[list[str]] = None,
    ) -> None:
        self.keys: list[bytes] = [self._resolve_key(channel_key_base64)]
        if extra_keys_base64:
            for k in extra_keys_base64:
                resolved = self._resolve_key(k)
                if resolved not in self.keys:
                    self.keys.append(resolved)

    @staticmethod
    def _resolve_key(key_b64: str) -> bytes:
        if not key_b64 or key_b64 == "AQ==":
            return DEFAULT_KEY_BYTES
        try:
            decoded = base64.b64decode(key_b64)
            return decoded.ljust(16, b"\x00")[:16]
        except Exception as exc:
            logger.warning("Invalid channel key, using default: %s", exc)
            return DEFAULT_KEY_BYTES

    def _aes_ctr(
        self, key: bytes, packet_id: int, from_node: int, data: bytes, encrypt: bool
    ) -> bytes:
        try:
            iv = packet_id.to_bytes(8, "little") + from_node.to_bytes(8, "little")
            cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
            op = cipher.encryptor() if encrypt else cipher.decryptor()
            return op.update(data) + op.finalize()
        except Exception as exc:
            logger.debug("AES-CTR failed: %s", exc)
            return b""

    def decrypt_payload(self, packet_id: int, from_node: int, encrypted_bytes: bytes) -> bytes:
        for key in self.keys:
            plain = self._aes_ctr(key, packet_id, from_node, encrypted_bytes, encrypt=False)
            if not plain:
                continue
            try:
                ds = mesh_pb2.Data()
                ds.ParseFromString(plain)
                if ds.portnum:
                    return plain
            except Exception:
                continue
        for key in self.keys:
            plain = self._aes_ctr(key, packet_id, from_node, encrypted_bytes, encrypt=False)
            if plain:
                return plain
        return b""

    def encrypt_payload(self, packet_id: int, from_node: int, plaintext_bytes: bytes) -> bytes:
        return self._aes_ctr(self.keys[0], packet_id, from_node, plaintext_bytes, encrypt=True)

    def decode_mqtt_payload(self, topic: str, raw_payload: bytes) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "UNKNOWN",
            "from_node": "UNKNOWN",
            "data": {},
            "topic": topic,
            "channel_hint": self._channel_from_topic(topic),
            "snr": None,
            "rssi": None,
            "hop_start": None,
            "hop_limit": None,
        }

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

            # RF metrics live on the MeshPacket itself
            if hasattr(packet, "rx_snr") and packet.rx_snr:
                result["snr"] = float(packet.rx_snr)
            if hasattr(packet, "rx_rssi") and packet.rx_rssi:
                result["rssi"] = int(packet.rx_rssi)
            if hasattr(packet, "hop_start") and packet.hop_start:
                result["hop_start"] = int(packet.hop_start)
            if hasattr(packet, "hop_limit") and packet.hop_limit:
                result["hop_limit"] = int(packet.hop_limit)

            if packet.HasField("encrypted") and packet.encrypted:
                plain = self.decrypt_payload(packet.id, from_node_val, packet.encrypted)
                if plain:
                    data_struct = mesh_pb2.Data()
                    data_struct.ParseFromString(plain)
                    return self._process_data_struct(data_struct, result)
            elif packet.HasField("decoded"):
                return self._process_data_struct(packet.decoded, result)

        except Exception as exc:
            logger.debug("Decode failed: %s", exc)

        if result["from_node"] != "UNKNOWN" and result["type"] == "UNKNOWN":
            result["type"] = "NODE_INFO"

        return result

    @staticmethod
    def _channel_from_topic(topic: str) -> str:
        parts = topic.split("/")
        for i, p in enumerate(parts):
            if p in ("c", "e") and i + 1 < len(parts):
                return parts[i + 1]
        return "unknown"

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

        elif portnum == portnums_pb2.PortNum.TELEMETRY_APP:
            result["type"] = "TELEMETRY"
            try:
                # Prefer telemetry_pb2 if available
                try:
                    from meshtastic import telemetry_pb2
                    tel = telemetry_pb2.Telemetry()
                    tel.ParseFromString(data_struct.payload)
                    data: dict[str, Any] = {}
                    if tel.HasField("device_metrics"):
                        dm = tel.device_metrics
                        if dm.battery_level:
                            data["battery_level"] = int(dm.battery_level)
                        if dm.voltage:
                            data["voltage"] = float(dm.voltage)
                        if dm.channel_utilization:
                            data["channel_utilization"] = float(dm.channel_utilization)
                        if dm.air_util_tx:
                            data["air_util_tx"] = float(dm.air_util_tx)
                    result["data"] = data
                except ImportError:
                    result["data"] = {"raw": "telemetry"}
            except Exception as exc:
                logger.debug("TELEMETRY parse error: %s", exc)

        else:
            result["type"] = f"PORTNUM_{portnum}"

        return result
