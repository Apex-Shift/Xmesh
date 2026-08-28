"""Node domain model with RF and telemetry fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Node:
    """Represents a single node on the Meshtastic mesh."""

    node_id: str
    short_name: str = "N/A"
    long_name: str = "N/A"
    hw_model: str = "N/A"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    snr: Optional[float] = None
    rssi: Optional[int] = None
    hop_start: Optional[int] = None
    battery_level: Optional[int] = None   # 0-100 or >100 = powered
    voltage: Optional[float] = None
    channel: str = ""
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0

    def update_info(
        self,
        short_name: Optional[str] = None,
        long_name: Optional[str] = None,
        hw_model: Optional[str] = None,
    ) -> None:
        if short_name:
            self.short_name = short_name
        if long_name:
            self.long_name = long_name
        if hw_model:
            self.hw_model = hw_model
        self.touch()

    def update_position(self, lat: float, lon: float, alt: float = 0.0) -> None:
        self.latitude = lat
        self.longitude = lon
        self.altitude = alt
        self.touch()

    def update_rf(
        self,
        snr: Optional[float] = None,
        rssi: Optional[int] = None,
        hop_start: Optional[int] = None,
    ) -> None:
        if snr is not None:
            self.snr = snr
        if rssi is not None:
            self.rssi = rssi
        if hop_start is not None:
            self.hop_start = hop_start
        self.touch()

    def update_telemetry(
        self,
        battery_level: Optional[int] = None,
        voltage: Optional[float] = None,
    ) -> None:
        if battery_level is not None:
            self.battery_level = battery_level
        if voltage is not None:
            self.voltage = voltage
        self.touch()

    def touch(self) -> None:
        self.last_seen = datetime.now(timezone.utc)

    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def display_name(self) -> str:
        if self.short_name and self.short_name not in ("N/A", "?"):
            return f"{self.short_name} ({self.node_id})"
        return self.node_id

    def battery_str(self) -> str:
        if self.battery_level is None:
            return ""
        if self.battery_level > 100:
            return "PWR"
        return f"{self.battery_level}%"
