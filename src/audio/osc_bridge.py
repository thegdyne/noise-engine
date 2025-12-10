"""
OSC Bridge
Handles communication with SuperCollider
"""

from pythonosc import udp_client
from src.config import OSC_HOST, OSC_SEND_PORT


class OSCBridge:
    """Manages OSC communication with SuperCollider."""
    
    def __init__(self):
        self.client = None
        self.connected = False
        
    def connect(self, host=None, port=None):
        """Connect to SuperCollider."""
        try:
            self.client = udp_client.SimpleUDPClient(
                host or OSC_HOST,
                port or OSC_SEND_PORT
            )
            self.connected = True
            print(f"✓ Connected to SuperCollider at {host or OSC_HOST}:{port or OSC_SEND_PORT}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
            
    def send_parameter(self, param_name, value):
        """Send parameter change to SuperCollider."""
        if self.client:
            osc_address = f"/noise/{param_name}"
            self.client.send_message(osc_address, [value])
