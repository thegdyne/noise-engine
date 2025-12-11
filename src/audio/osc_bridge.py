"""
OSC Bridge
Handles bidirectional communication with SuperCollider
- Sends commands to SC on port 57120
- Receives gate triggers from SC on port 57121
"""

from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
import threading
from src.config import OSC_HOST, OSC_SEND_PORT, OSC_RECEIVE_PORT


class OSCBridge:
    """Manages OSC communication with SuperCollider."""
    
    def __init__(self):
        self.client = None
        self.server = None
        self.server_thread = None
        self.connected = False
        self.gate_callback = None  # Callback for gate triggers
        
    def connect(self, host=None, port=None):
        """Connect to SuperCollider and start receiving."""
        try:
            # Outgoing client (to SC)
            self.client = udp_client.SimpleUDPClient(
                host or OSC_HOST,
                port or OSC_SEND_PORT
            )
            
            # Incoming server (from SC)
            self._start_server()
            
            self.connected = True
            print(f"✓ Connected to SuperCollider at {host or OSC_HOST}:{port or OSC_SEND_PORT}")
            print(f"✓ Listening for SC messages on port {OSC_RECEIVE_PORT}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    def _start_server(self):
        """Start OSC server to receive messages from SC."""
        dispatcher = Dispatcher()
        
        # Handle gate triggers from SC
        dispatcher.map("/noise/midi/gate", self._handle_gate)
        
        # Catch-all for debugging
        dispatcher.set_default_handler(self._default_handler)
        
        try:
            self.server = ThreadingOSCUDPServer(
                ("127.0.0.1", OSC_RECEIVE_PORT),
                dispatcher
            )
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
        except Exception as e:
            print(f"Warning: Could not start OSC receive server: {e}")
    
    def _handle_gate(self, address, *args):
        """Handle gate trigger from SC."""
        if len(args) > 0 and self.gate_callback:
            slot_id = int(args[0])
            self.gate_callback(slot_id)
    
    def _default_handler(self, address, *args):
        """Default handler for unknown messages."""
        # Uncomment for debugging:
        # print(f"OSC received: {address} {args}")
        pass
    
    def set_gate_callback(self, callback):
        """Set callback for gate triggers. callback(slot_id)"""
        self.gate_callback = callback
            
    def send_parameter(self, param_name, value):
        """Send parameter change to SuperCollider."""
        if self.client:
            osc_address = f"/noise/{param_name}"
            self.client.send_message(osc_address, [value])
    
    def disconnect(self):
        """Disconnect and clean up."""
        if self.server:
            self.server.shutdown()
            self.server = None
        self.client = None
        self.connected = False
