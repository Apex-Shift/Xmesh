# XMESH – Expert Meshtastic MQTT Monitor

**Version 2.1.0** · Production-ready · Tactical dark UI · AES-128-CTR · Protobuf

XMESH is a high-performance desktop client that connects to any Meshtastic MQTT broker, decrypts live mesh traffic, maintains a real-time node database, displays chat and GPS telemetry, and lets you broadcast text messages back onto the network.

---

## Features

| Area | Capability |
|------|------------|
| **Transport** | `paho-mqtt` with automatic reconnect, TLS support, QoS 0 wildcard subscriptions |
| **Crypto** | AES-128-CTR with the official Meshtastic IV construction (`packet_id \|\| from_node`) |
| **Protocol** | Full decode of `TEXT_MESSAGE_APP`, `NODEINFO_APP`, `POSITION_APP` via official `meshtastic` protobufs |
| **UI** | PySide6 tactical dark theme, live stats, node table, coloured chat with timestamps, position telemetry table |
| **Architecture** | Clean separation (core / models / ui), Qt signal bus, type-hinted code, structured logging |
| **Packaging** | `pyproject.toml`, MIT license, pinned dependencies |

---

## Project Layout

```
Xmesh-expert/
├── core/
│   ├── mqtt_client.py      # MQTT client + reconnect + TLS
│   ├── protobuf_decoder.py # AES-CTR + ServiceEnvelope / MeshPacket decode
│   └── signals.py          # Qt signal bus
├── models/
│   └── node.py             # Dataclass Node model
├── ui/
│   ├── main_window.py      # Main window + stats + navigation
│   ├── styles/theme.qss    # High-contrast tactical theme
│   └── widgets/
│       ├── chat.py         # Live chat + send
│       ├── node_list.py    # Node DB table
│       └── map_view.py     # Position telemetry table
├── config.yaml             # Broker + channel key
├── main.py                 # Entry point
├── requirements.txt
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## Requirements

- **Python 3.10+** (3.12 recommended)
- OS: Linux / Windows / macOS

---

## Installation

```bash
# 1. Extract / clone
cd Xmesh-expert

# 2. (Optional but recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Edit `config.yaml`:

```yaml
mqtt:
  broker: "mqtt.meshtastic.org"
  port: 1883                  # 8883 for TLS
  username: "meshdev"
  password: "large4cats"
  use_tls: false
  topic: "msh/+/2/c/LongFast/#"

mesh:
  channel_key_base64: "AQ=="  # Default public LongFast key
```

> **Private channel** – replace `channel_key_base64` with your 16-byte PSK encoded in Base64.

---

## Launch

Always run from the project root so that relative paths resolve correctly:

```bash
python main.py
```

---

## Operational Notes

- **Node DB** – Every packet that carries a node identity populates or refreshes the table (short name, long name, hardware model, last-seen timestamp).
- **Live Chat** – Incoming `TEXT_MESSAGE_APP` packets appear with timestamps. Type a message and press **Enter** or click **SEND** to encrypt and publish a broadcast.
- **Telemetry** – `POSITION_APP` packets feed the position table (lat / lon / altitude). The data model is ready for a future map widget (folium, pyqt-leaflet, etc.).
- **Connection status** – The top-right card and the status bar reflect online / offline state in real time.
- **TLS** – Set `use_tls: true` and `port: 8883` for encrypted transport to the public broker or your own Mosquitto instance.

---

## Technical Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| GUI | PySide6 (Qt 6) |
| MQTT | paho-mqtt |
| Crypto | cryptography (AES-128-CTR) |
| Serialization | meshtastic protobufs (`mesh_pb2`, `mqtt_pb2`, `portnums_pb2`) |
| Config | PyYAML |

---

## Security Notes

- The default key `"AQ=="` is the **public** Meshtastic LongFast channel. Anyone can decrypt traffic on that channel.
- For private deployments generate a random 16-byte key, Base64-encode it, and distribute it only to authorised nodes.
- Credentials in `config.yaml` should never be committed to public repositories when using private brokers.

---

## License

MIT License – see [LICENSE](LICENSE).

---

## Changelog (v2.1.0 – Expert Edition)

- Unified and corrected AES-CTR key handling (official default key)
- Full TLS support + robust reconnect / status signals
- Professional sidebar navigation (QListWidget)
- Live connection / node / message counters
- Timestamps and colour coding in chat
- Proper Node dataclass with last-seen tracking
- Position telemetry table (map-ready)
- Type hints, docstrings, structured logging throughout
- `pyproject.toml`, `.gitignore`, MIT license
- Cleaner configuration and README
