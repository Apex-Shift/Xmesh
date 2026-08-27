import base64
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class MeshCrypto:
    def __init__(self, key_base64: str = "AQ=="):
        self.default_key = b'\xd4\xf1\xbb: \xbd\xc3D\xf9-\x07`\x1c\x86\xea|'
        if key_base64 == "AQ==":
            self.key = self.default_key
        else:
            try:
                self.key = base64.b64decode(key_base64)
            except Exception as e:
                logger.error(f"Error decoding base64 key: {e}")
                self.key = self.default_key

    def decrypt(self, from_node: int, packet_id: int, encrypted_data: bytes) -> bytes:
        try:
            nonce = packet_id.to_bytes(8, 'little') + from_node.to_bytes(8, 'little')
            cipher = Cipher(
                algorithms.AES(self.key), 
                modes.CTR(nonce), 
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            return decryptor.update(encrypted_data) + decryptor.finalize()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return b""