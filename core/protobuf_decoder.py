import base64
import logging
from meshtastic import mesh_pb2, portnums_pb2, mqtt_pb2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

DEFAULT_KEY_BYTES = bytes([
    0xd4, 0xf1, 0xbb, 0x3a, 0x20, 0x29, 0x07, 0x59,
    0xf0, 0xbc, 0xff, 0xab, 0xcf, 0x4e, 0x69, 0x01
])

class ProtobufDecoder:
    def __init__(self, channel_key_base64: str = "AQ=="):
        if channel_key_base64 == "AQ==":
            self.key = DEFAULT_KEY_BYTES
        else:
            try:
                decoded = base64.b64decode(channel_key_base64)
                self.key = decoded.ljust(16, b'\x00')[:16]
            except Exception:
                self.key = DEFAULT_KEY_BYTES

    def decrypt_payload(self, packet_id: int, from_node: int, encrypted_bytes: bytes) -> bytes:
        try:
            iv = packet_id.to_bytes(8, byteorder='little') + from_node.to_bytes(8, byteorder='little')
            cipher = Cipher(algorithms.AES(self.key), modes.CTR(iv), backend=default_backend())
            return cipher.decryptor().update(encrypted_bytes) + cipher.decryptor().finalize()
        except Exception:
            return b""

    def encrypt_payload(self, packet_id: int, from_node: int, plaintext_bytes: bytes) -> bytes:
        try:
            iv = packet_id.to_bytes(8, byteorder='little') + from_node.to_bytes(8, byteorder='little')
            cipher = Cipher(algorithms.AES(self.key), modes.CTR(iv), backend=default_backend())
            return cipher.encryptor().update(plaintext_bytes) + cipher.encryptor().finalize()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return b""

    def decode_mqtt_payload(self, topic: str, raw_payload: bytes) -> dict:
        result = {"type": "UNKNOWN", "from_node": "UNKNOWN", "data": {}}

        topic_parts = topic.split("/")
        if topic_parts and topic_parts[-1].startswith("!"):
            result["from_node"] = topic_parts[-1]

        try:
            envelope = mqtt_pb2.ServiceEnvelope()
            envelope.ParseFromString(raw_payload)
            packet = envelope.packet
            
            from_node_val = getattr(packet, "from", 0) or packet.from_node
            if from_node_val:
                result["from_node"] = f"!{from_node_val:08x}"

            payload_bytes = b""
            if packet.HasField("encrypted") and packet.encrypted:
                payload_bytes = self.decrypt_payload(packet.id, from_node_val, packet.encrypted)
            elif packet.HasField("decoded"):
                return self._process_data_struct(packet.decoded, result)

            if payload_bytes:
                data_struct = mesh_pb2.Data()
                data_struct.ParseFromString(payload_bytes)
                return self._process_data_struct(data_struct, result)

        except Exception:
            pass

        if result["from_node"] != "UNKNOWN" and result["type"] == "UNKNOWN":
            result["type"] = "NODE_INFO"

        return result

    def _process_data_struct(self, data_struct, result) -> dict:
        portnum = data_struct.portnum

        if portnum == portnums_pb2.PortNum.TEXT_MESSAGE_APP:
            result["type"] = "TEXT_MESSAGE"
            result["data"] = data_struct.payload.decode("utf-8", errors="ignore")

        elif portnum == portnums_pb2.PortNum.NODEINFO_APP:
            result["type"] = "NODE_INFO"
            try:
                user = mesh_pb2.User()
                user.ParseFromString(data_struct.payload)
                result["data"] = {
                    "short_name": user.short_name,
                    "long_name": user.long_name,
                    "hw_model": mesh_pb2.HardwareModel.Name(user.hw_model)
                }
            except Exception:
                pass

        elif portnum == portnums_pb2.PortNum.POSITION_APP:
            result["type"] = "POSITION"
            try:
                pos = mesh_pb2.Position()
                pos.ParseFromString(data_struct.payload)
                result["data"] = {
                    "latitude": pos.latitude_i / 1e7 if pos.latitude_i else 0.0,
                    "longitude": pos.longitude_i / 1e7 if pos.longitude_i else 0.0,
                    "altitude": pos.altitude if pos.altitude else 0
                }
            except Exception:
                pass
        else:
            result["type"] = "NODE_INFO"

        return result