import logging
import random
import paho.mqtt.client as mqtt
from meshtastic import mesh_pb2, portnums_pb2, mqtt_pb2
from core.protobuf_decoder import ProtobufDecoder
from core.signals import MeshSignals

logger = logging.getLogger(__name__)

class MeshtasticMQTTClient:
    def __init__(self, broker: str, port: int, topic: str, username: str = "meshdev", password: str = "large4cats", use_tls: bool = False, channel_key: str = "AQ==", signals: MeshSignals = None):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.signals = signals
        
        self.my_node_num = random.randint(0x10000000, 0x7FFFFFFF)
        self.my_node_hex = f"!{self.my_node_num:08x}"
        
        client_id = f"xmesh_{self.my_node_hex[1:]}"
        self.client = mqtt.Client(client_id=client_id)
        
        if username and password:
            self.client.username_pw_set(username, password)

        self.decoder = ProtobufDecoder(channel_key_base64=channel_key)
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        if self.signals:
            self.signals.send_message_requested.connect(self.send_text_message)

    def connect(self) -> None:
        logger.info(f"Connecting to live broker {self.broker}:{self.port}...")
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def disconnect(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def send_text_message(self, text: str) -> None:
        if not text:
            return

        packet_id = random.randint(1, 0xFFFFFFFF)
        
        # Build Data payload
        data_struct = mesh_pb2.Data()
        data_struct.portnum = portnums_pb2.PortNum.TEXT_MESSAGE_APP
        data_struct.payload = text.encode('utf-8')
        
        # Encrypt payload
        encrypted_bytes = self.decoder.encrypt_payload(packet_id, self.my_node_num, data_struct.SerializeToString())
        
        # Build MeshPacket
        mesh_packet = mesh_pb2.MeshPacket()
        setattr(mesh_packet, "from", self.my_node_num)
        mesh_packet.to = 0xFFFFFFFF
        mesh_packet.id = packet_id
        mesh_packet.encrypted = encrypted_bytes
        mesh_packet.channel = 0
        
        # Wrap inside ServiceEnvelope using mqtt_pb2
        envelope = mqtt_pb2.ServiceEnvelope()
        envelope.packet.CopyFrom(mesh_packet)
        envelope.channel_id = "LongFast"
        envelope.gateway_id = self.my_node_hex
        
        pub_topic = f"msh/EU_868/2/c/LongFast/{self.my_node_hex}"
        self.client.publish(pub_topic, envelope.SerializeToString())
        logger.info(f"📤 Sent message on [{pub_topic}]: {text}")
        
        if self.signals:
            self.signals.message_received.emit({
                "type": "TEXT_MESSAGE",
                "from_node": f"{self.my_node_hex} (YOU)",
                "data": text
            })

    def on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            logger.info("CONNECTED TO LIVE NETWORK!")
            self.client.subscribe(self.topic)

    def on_message(self, client, userdata, msg) -> None:
        try:
            packet = self.decoder.decode_mqtt_payload(msg.topic, msg.payload)
            if not packet:
                return

            packet_type = str(packet.get("type", "")).upper()
            from_node = packet.get("from_node", "UNKNOWN")

            if self.signals:
                if from_node != "UNKNOWN":
                    self.signals.node_updated.emit({
                        "type": "NODE_INFO",
                        "from_node": from_node,
                        "data": packet.get("data", {}) if isinstance(packet.get("data"), dict) else {}
                    })

                if "TEXT" in packet_type:
                    self.signals.message_received.emit(packet)
                elif "POSITION" in packet_type:
                    self.signals.position_updated.emit(packet)

        except Exception as e:
            logger.error(f"Error processing packet: {e}")

    def on_disconnect(self, client, userdata, rc) -> None:
        if rc != 0:
            logger.warning(f"Connection lost (rc={rc}). Reconnecting...")