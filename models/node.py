class Node:
    """Model representing a Meshtastic network node."""
    def __init__(self, node_id: str, short_name: str = "N/A", long_name: str = "N/A", hw_model: str = "N/A"):
        self.node_id = node_id
        self.short_name = short_name
        self.long_name = long_name
        self.hw_model = hw_model
        self.latitude = None
        self.longitude = None
        self.altitude = None

    def update_info(self, short_name: str, long_name: str, hw_model: str):
        self.short_name = short_name or self.short_name
        self.long_name = long_name or self.long_name
        self.hw_model = hw_model or self.hw_model

    def update_position(self, lat: float, lon: float, alt: float = 0):
        self.latitude = lat
        self.longitude = lon
        self.altitude = alt