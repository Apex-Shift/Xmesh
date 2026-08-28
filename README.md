# XMESH  
<img width="1365" height="695" alt="image" src="https://github.com/user-attachments/assets/56e43c08-85cd-420b-8689-f9f6ba692d1a" />
<img width="1162" height="435" alt="image" src="https://github.com/user-attachments/assets/991806d4-db28-4f85-a7c1-288cbb601251" />
<img width="1159" height="658" alt="image" src="https://github.com/user-attachments/assets/3b919fb7-7db4-4436-ac6b-9f890e262cf4" />

**Version 2.2** · SNR/RSSI · Device telemetry · Search · Logs · Interactive map · CSV

Desktop client that connects to any Meshtastic MQTT broker, decrypts live traffic, tracks nodes with RF metrics, shows chat & GPS, opens a Leaflet map, and exports CSV.

---

## What's new in v2.2

- **SNR / RSSI / hops** extracted from every MeshPacket and shown in Node DB + chat
- **Device telemetry** (`TELEMETRY_APP`) → battery % / voltage on nodes
- **Search / filter** on Node DB and Live Chat
- **Context menu** on nodes → copy ID, coordinates, display name
- **Logs tab** with colour-coded INFO / WARN / ERROR (also `Ctrl+L`)
- **Packet counter** in the stats bar
- Clear chat / clear filter buttons
- Richer CSV exports (SNR, RSSI, battery, voltage)

---

## Features overview

| Area | Capability |
|------|------------|
| Transport | paho-mqtt · auto-reconnect · TLS · multi-topic |
| Crypto | AES-128-CTR · multi-PSK |
| Protocol | TEXT · NODEINFO · POSITION · TELEMETRY |
| RF metrics | SNR, RSSI, hop_start |
| UI | Dark tactical theme · 4 views · live stats |
| Map | Leaflet (folium) dark tiles + MarkerCluster |
| Export | CSV nodes / messages / positions |
| UX | Search, clipboard, logs, shortcuts |

---

## Install

```bash
cd Xmesh-expert
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Config (`config.yaml`)

```yaml
mqtt:
  broker: "mqtt.meshtastic.org"
  port: 1883
  username: "meshdev"
  password: "large4cats"
  use_tls: false
  topics:
    - "msh/+/2/c/LongFast/#"

mesh:
  channel_key_base64: "AQ=="
  # extra_keys_base64:
  #   - "AnotherKeyBase64=="
```

---

## Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+E` | Export nodes CSV |
| `Ctrl+M` | Export messages CSV |
| `Ctrl+Shift+M` | Open interactive map |
| `Ctrl+L` | Jump to Logs tab |

Right-click a row in **Node DB** to copy ID or coordinates.

---

## License

MIT
