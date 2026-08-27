# XMESH  

> A professional, high-performance desktop monitoring and control client built with Python, PySide6, and MQTT for interacting with the global decentralized Meshtastic mesh network.

---

## 🚀 Overview

**XMESH** is engineered as a tactical operations center for Meshtastic networks. It hooks directly into MQTT message brokers to intercept, decode, encrypt, and broadcast network packets across regional meshes in real-time. Whether you are monitoring telemetry from solar relays, tracking node hardware distributions, or sending encrypted broadcasts across public/private channels, XMESH provides a responsive, dark-themed tactical UI.

---

## 🛠️ Architecture & Core Components

```text
Xmesh/
├── core/
│   ├── __init__.py
│   ├── mqtt_client.py        # Asynchronous MQTT connection engine & packet publisher
│   ├── protobuf_decoder.py   # AES-128-CTR crypto pipeline & Protobuf parser
│   └── signals.py            # PySide6 cross-thread event mapping
├── ui/
│   ├── widgets/
│   │   ├── chat.py           # Real-time encrypted text broadcast & chat feed
│   │   ├── map_view.py       # GPS position & telemetry visualization interface
│   │   └── node_list.py      # Dynamic active node database (Node DB)
│   ├── styles/
│   │   └── theme.qss         # Custom high-contrast tactical dark theme
│   └── main_window.py        # Central layout container & telemetry counters
├── config.yaml               # Broker configuration and channel security keys
├── requirements.txt          # Python package dependencies
└── main.py                   # Application entry point
```

---

## ⚙️ Technical Specifications

* **Language**: Python 3.12+
* **GUI Framework**: PySide6 (Qt for Python)
* **Transport Layer**: `paho-mqtt` (MQTT client implementation with QoS and topic filtering)
* **Cryptography**: `cryptography` library utilizing AES-128-CTR mode with dynamically generated IVs (packet ID + sender node mapping)
* **Protocol Serialization**: Google Protocol Buffers via official `meshtastic` packages (`mqtt_pb2`, `mesh_pb2`, `portnums_pb2`)

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/apex-shift/Xmesh.git
cd Xmesh
```

### 2. Install Dependencies
Ensure you have Python installed, then run:
```bash
pip install -r requirements.txt
```

### 3. Configure Parameters (config.yaml)
Create or update your `config.yaml` file in the root project directory:
```yaml
mqtt:
  broker: "mqtt.meshtastic.org"
  port: 8883
  username: "meshdev"
  password: "large4ree"
  use_tls: true
  topic: "msh/+/2/c/LongFast/#"

mesh:
  channel_key_base64: "AQ=="  # Default standard LongFast channel key
```

### 4. Launch the Application
Always run the application from the project root directory:
```bash
python main.py
```

---

## 🕹️ Operational Guidelines

* **Node Database (Node DB)**: Upon successful connection to the MQTT broker, the system automatically subscribes to regional wildcards. Incoming telemetry and node info frames (`NODEINFO_APP`) dynamically populate active nodes with hardware details (`HELTEC_V3`, `RAK4631`, etc.).
* **Live Chat & Broadcasting**: Switch to the Live Chat tab to view intercepted text streams. Type your broadcast message into the terminal input field and hit Enter or click Send. The client will package your text into a Data structure, encrypt it using AES-128-CTR, wrap it inside a ServiceEnvelope, and publish it to the mesh network.
* **Telemetry & Mapping**: Intercepted GPS packets (`POSITION_APP`) track global node coordinates in real-time.
