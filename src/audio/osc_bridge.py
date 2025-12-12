"""
OSC Bridge
Handles bidirectional communication with SuperCollider

Connection features:
- Ping/pong verification on connect
- Heartbeat monitoring during performance
- Connection lost detection with callback
- One-click reconnect capability

Ports:
- Sends to SC on port 57120 (fixed in SC init.scd)
- Receives from SC on port 57121
"""

from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class OSCBridge(QObject):
    """Manages OSC communication with SuperCollider."""
    
    # Signals for thread-safe notifications
    gate_triggered = pyqtSignal(int)  # slot_id
    connection_lost = pyqtSignal()  # Emitted when heartbeat fails
    connection_restored = pyqtSignal()  # Emitted when reconnect succeeds
    
    # Connection constants
    PING_TIMEOUT_MS = 1000  # Wait 1 second for ping response
    HEARTBEAT_INTERVAL_MS = 2000  # Send heartbeat every 2 seconds
    HEARTBEAT_MISS_LIMIT = 3  # Connection lost after 3 missed heartbeats
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.server = None
        self.server_thread = None
        self.connected = False
        
        # Connection verification
        self._ping_received = False
        self._heartbeat_received = False
        self._missed_heartbeats = 0
        
        # Heartbeat timer
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._check_heartbeat)
        
        # Store connection params for reconnect
        self._host = None
        self._port = None
        
    def connect(self, host=None, port=None):
        """Connect to SuperCollider with verification."""
        from src.config import OSC_HOST, OSC_SEND_PORT
        
        self._host = host or OSC_HOST
        self._port = port or OSC_SEND_PORT
        
        try:
            # Start receiver first (to catch pong)
            self._start_server()
            
            # Create client
            self.client = udp_client.SimpleUDPClient(self._host, self._port)
            
            # Verify connection with ping
            if not self._verify_connection():
                self._cleanup()
                print(f"✗ SuperCollider not responding on port {self._port}")
                print(f"  Check: NetAddr.langPort.postln; in SC")
                return False
            
            self.connected = True
            self._missed_heartbeats = 0
            
            # Start heartbeat monitoring
            self._heartbeat_timer.start(self.HEARTBEAT_INTERVAL_MS)
            
            print(f"✓ Connected to SuperCollider at {self._host}:{self._port}")
            print(f"✓ Listening for SC messages on port 57121")
            print(f"✓ Heartbeat monitoring active")
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            self._cleanup()
            return False
    
    def _verify_connection(self):
        """Send ping and wait for pong response."""
        self._ping_received = False
        
        # Send ping
        self.client.send_message('/noise/ping', [1])
        
        # Wait for pong (blocking with timeout)
        start_time = time.time()
        timeout_sec = self.PING_TIMEOUT_MS / 1000.0
        
        while not self._ping_received:
            if time.time() - start_time > timeout_sec:
                return False
            time.sleep(0.05)  # 50ms polling
        
        return True
    
    def _check_heartbeat(self):
        """Called by timer - send heartbeat and check for response."""
        if not self.connected or not self.client:
            return
        
        # Check if we got response from last heartbeat
        if not self._heartbeat_received:
            self._missed_heartbeats += 1
            if self._missed_heartbeats >= self.HEARTBEAT_MISS_LIMIT:
                print(f"✗ CONNECTION LOST - {self.HEARTBEAT_MISS_LIMIT} missed heartbeats")
                self.connected = False
                self._heartbeat_timer.stop()
                self.connection_lost.emit()
                return
        else:
            # Got response, reset counter
            if self._missed_heartbeats > 0:
                print("✓ Connection restored")
                self._missed_heartbeats = 0
        
        # Send next heartbeat
        self._heartbeat_received = False
        try:
            self.client.send_message('/noise/heartbeat', [1])
        except Exception as e:
            print(f"✗ Heartbeat send failed: {e}")
            self._missed_heartbeats += 1
    
    def reconnect(self):
        """Attempt to reconnect using stored parameters."""
        print("Attempting reconnect...")
        self._cleanup()
        time.sleep(0.1)  # Brief pause
        
        if self.connect(self._host, self._port):
            self.connection_restored.emit()
            return True
        return False
    
    def _start_server(self):
        """Start OSC server to receive messages from SC."""
        from src.config import OSC_RECEIVE_PORT
        
        dispatcher = Dispatcher()
        
        # Connection management
        dispatcher.map("/noise/pong", self._handle_pong)
        dispatcher.map("/noise/heartbeat_ack", self._handle_heartbeat_ack)
        
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
    
    def _handle_pong(self, address, *args):
        """Handle pong response from SC."""
        self._ping_received = True
    
    def _handle_heartbeat_ack(self, address, *args):
        """Handle heartbeat acknowledgment from SC."""
        self._heartbeat_received = True
    
    def _handle_gate(self, address, *args):
        """Handle gate trigger from SC - emit signal for thread safety."""
        if len(args) > 0:
            slot_id = int(args[0])
            self.gate_triggered.emit(slot_id)
    
    def _default_handler(self, address, *args):
        """Default handler for unknown messages."""
        # Uncomment for debugging:
        # print(f"OSC received: {address} {args}")
        pass
            
    def send_parameter(self, param_name, value):
        """Send parameter change to SuperCollider."""
        if self.client:
            osc_address = f"/noise/{param_name}"
            self.client.send_message(osc_address, [value])
    
    def _cleanup(self):
        """Clean up connection resources."""
        self._heartbeat_timer.stop()
        if self.server:
            try:
                self.server.shutdown()
            except:
                pass
            self.server = None
        self.client = None
        self.connected = False
    
    def disconnect(self):
        """Disconnect and clean up."""
        self._cleanup()
        print("✓ Disconnected from SuperCollider")
    
    def is_healthy(self):
        """Check if connection is healthy (no missed heartbeats)."""
        return self.connected and self._missed_heartbeats == 0
