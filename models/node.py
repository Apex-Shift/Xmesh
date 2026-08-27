"""Node domain model."""

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

    def update_position(
        self,
        lat: float,
        lon: float,
        alt: float = 0.0,
    ) -> None:
        self.latitude = lat
        self.longitude = lon
        self.altitude = alt
        self.touch()

    def touch(self) -> None:
        self.last_seen = datetime.now(timezone.utc)

    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def display_name(self) -> str:
        if self.short_name and self.short_name != "N/A":
            return f"{self.short_name} ({self.node_id})"
        return self.node_id
