import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from ui.main_window import XmeshMainWindow
from core.mqtt_client import MeshtasticMQTTClient
from core.signals import MeshSignals
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def load_config():
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}

def main():
    app = QApplication(sys.argv)
    
    # Apply stylesheet to fix dark theme and sidebar styling
    for path in [Path("ui/styles/theme.qss"), Path("styles/theme.qss")]:
        if path.exists():
            with open(path, "r") as f:
                app.setStyleSheet(f.read())
            break

    signals = MeshSignals()
    
    config = load_config()
    mqtt_cfg = config.get("mqtt", {})
    mesh_cfg = config.get("mesh", {})
    
    broker = mqtt_cfg.get("broker") or "mqtt.meshtastic.org"
    port = int(mqtt_cfg.get("port") or 1883)
    topic = mqtt_cfg.get("topic") or "msh/+/2/c/LongFast/#"
    username = mqtt_cfg.get("username") or "meshdev"
    password = mqtt_cfg.get("password") or "large4cats"
    use_tls = mqtt_cfg.get("use_tls", False)
    channel_key = mesh_cfg.get("channel_key_base64") or "AQ=="

    mqtt_client = MeshtasticMQTTClient(
        broker=broker,
        port=port,
        topic=topic,
        username=username,
        password=password,
        use_tls=use_tls,
        channel_key=channel_key,
        signals=signals
    )
    mqtt_client.connect()

    window = XmeshMainWindow(signals=signals)
    window.show()

    exit_code = app.exec()
    mqtt_client.disconnect()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()