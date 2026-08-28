#!/usr/bin/env python3
"""XMESH – Expert Meshtastic MQTT Monitor v2.2

    python main.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml
from PySide6.QtWidgets import QApplication

from core.mqtt_client import MeshtasticMQTTClient
from core.signals import MeshSignals
from ui.main_window import XmeshMainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("xmesh")


def load_config() -> dict:
    config_path = Path(__file__).resolve().parent / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            logger.info("Loaded configuration from %s", config_path)
            return data
    logger.warning("config.yaml not found – using built-in defaults")
    return {}


def apply_stylesheet(app: QApplication) -> None:
    for candidate in (
        Path(__file__).resolve().parent / "ui" / "styles" / "theme.qss",
        Path("ui/styles/theme.qss"),
    ):
        if candidate.exists():
            app.setStyleSheet(candidate.read_text(encoding="utf-8"))
            return
    logger.warning("No theme.qss found")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("XMESH")
    app.setOrganizationName("Xmesh")
    apply_stylesheet(app)

    signals = MeshSignals()
    config = load_config()

    mqtt_cfg = config.get("mqtt", {})
    mesh_cfg = config.get("mesh", {})

    broker = mqtt_cfg.get("broker") or "mqtt.meshtastic.org"
    port = int(mqtt_cfg.get("port") or 1883)
    username = mqtt_cfg.get("username") or "meshdev"
    password = mqtt_cfg.get("password") or "large4cats"
    use_tls = bool(mqtt_cfg.get("use_tls", False))

    topics = mqtt_cfg.get("topics")
    if not topics:
        single = mqtt_cfg.get("topic") or "msh/+/2/c/LongFast/#"
        topics = [single]

    channel_key = mesh_cfg.get("channel_key_base64") or "AQ=="
    extra_keys = mesh_cfg.get("extra_keys_base64") or []

    mqtt_client = MeshtasticMQTTClient(
        broker=broker,
        port=port,
        topics=topics,
        username=username,
        password=password,
        use_tls=use_tls,
        channel_key=channel_key,
        extra_keys=extra_keys if isinstance(extra_keys, list) else [],
        signals=signals,
    )
    mqtt_client.connect()

    window = XmeshMainWindow(signals=signals)
    window.show()

    exit_code = app.exec()
    mqtt_client.disconnect()
    logger.info("Application closed (code=%s)", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
