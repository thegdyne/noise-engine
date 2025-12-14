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

from src.utils.logger import logger


class OSCBridge(QObject):
    """Manages OSC communication with SuperCollider."""
    
    # Signals for thread-safe notifications
    gate_triggered = pyqtSignal(int)  # slot_id
    levels_received = pyqtSignal(float, float, float, float)  # ampL, ampR, peakL, peakR
    channel_levels_received = pyqtSignal(int, float, float)  # slot_id, ampL, ampR
    comp_gr_received = pyqtSignal(float)  # compressor gain reduction in dB
    connection_lost = pyqtSignal()  # Emitted when heartbeat fails
    connection_restored = pyqtSignal()  # Emitted when reconnect succeeds
    # Audio device signals
    audio_devices_received = pyqtSignal(list, str)  # devices list, current device
    audio_device_changing = pyqtSignal(str)  # device name
    audio_device_ready = pyqtSignal(str)  # device name
    audio_device_error = pyqtSignal(str)  # error message
    
    # Connection constants
    PING_TIMEOUT_MS = 1000  # Wait 1 second for ping response
    HEARTBEAT_INTERVAL_MS = 2000  # Send heartbeat every 2 seconds
    HEARTBEAT_MISS_LIMIT = 3  # Connection lost after 3 missed heartbeats
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.server = None
        self.server_thread = None
        # Audio device query state
        self._audio_devices = []
        self._audio_device_current = ""
        self._audio_device_count = 0
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
                logger.error(f"SuperCollider not responding on port {self._port}", component="OSC")
                logger.info("Check: NetAddr.langPort.postln; in SC", component="OSC")
                return False
            
            self.connected = True
            self._missed_heartbeats = 0
            
            # Start heartbeat monitoring
            self._heartbeat_timer.start(self.HEARTBEAT_INTERVAL_MS)
            
            logger.info(f"Connected to SuperCollider at {self._host}:{self._port}", component="OSC")
            logger.debug(f"Listening for SC messages on port 57121", component="OSC")
            logger.debug("Heartbeat monitoring active", component="OSC")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}", component="OSC")
            self._cleanup()
            return False
    
    def _verify_connection(self):
        """Send ping and wait for pong response."""
        from src.config import OSC_PATHS
        
        self._ping_received = False
        
        # Send ping
        self.client.send_message(OSC_PATHS['ping'], [1])
        
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
        from src.config import OSC_PATHS
        
        if not self.connected or not self.client:
            return
        
        # Check if we got response from last heartbeat
        if not self._heartbeat_received:
            self._missed_heartbeats += 1
            if self._missed_heartbeats >= self.HEARTBEAT_MISS_LIMIT:
                logger.error(f"CONNECTION LOST - {self.HEARTBEAT_MISS_LIMIT} missed heartbeats", component="OSC")
                self.connected = False
                self._heartbeat_timer.stop()
                self.connection_lost.emit()
                return
        else:
            # Got response, reset counter
            if self._missed_heartbeats > 0:
                logger.info("Connection restored", component="OSC")
                self._missed_heartbeats = 0
        
        # Send next heartbeat
        self._heartbeat_received = False
        try:
            self.client.send_message(OSC_PATHS['heartbeat'], [1])
        except Exception as e:
            logger.warning(f"Heartbeat send failed: {e}", component="OSC")
            self._missed_heartbeats += 1
    
    def reconnect(self):
        """Attempt to reconnect using stored parameters."""
        logger.info("Attempting reconnect...", component="OSC")
        self._cleanup()
        time.sleep(0.1)  # Brief pause
        
        if self.connect(self._host, self._port):
            self.connection_restored.emit()
            return True
        return False
    
    def _start_server(self):
        """Start OSC server to receive messages from SC."""
        from src.config import OSC_RECEIVE_PORT, OSC_PATHS
        
        dispatcher = Dispatcher()
        
        # Connection management
        dispatcher.map(OSC_PATHS['pong'], self._handle_pong)
        dispatcher.map(OSC_PATHS['heartbeat_ack'], self._handle_heartbeat_ack)
        
        # Handle gate triggers from SC
        dispatcher.map(OSC_PATHS['midi_gate'], self._handle_gate)
        
        # Handle level meter data from SC
        dispatcher.map(OSC_PATHS['master_levels'], self._handle_levels)
        
        # Handle per-channel level meter data from SC
        dispatcher.map(OSC_PATHS['gen_levels'], self._handle_channel_levels)
        
        # Handle compressor GR from SC
        dispatcher.map(OSC_PATHS['master_comp_gr'], self._handle_comp_gr)
        
        # Handle audio device messages from SC
        dispatcher.map(OSC_PATHS['audio_devices_count'], self._handle_audio_devices_count)
        dispatcher.map(OSC_PATHS['audio_devices_item'], self._handle_audio_devices_item)
        dispatcher.map(OSC_PATHS['audio_devices_done'], self._handle_audio_devices_done)
        dispatcher.map(OSC_PATHS['audio_device_changing'], self._handle_audio_device_changing)
        dispatcher.map(OSC_PATHS['audio_device_ready'], self._handle_audio_device_ready)
        dispatcher.map(OSC_PATHS['audio_device_error'], self._handle_audio_device_error)
        
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
            logger.warning(f"Could not start OSC receive server: {e}", component="OSC")
    
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
    
    def _handle_levels(self, address, *args):
        """Handle level meter data from SC."""
        # Now receiving direct values: [ampL, ampR, peakL, peakR]
        if len(args) >= 4:
            amp_l = float(args[0])
            amp_r = float(args[1])
            peak_l = float(args[2])
            peak_r = float(args[3])
            self.levels_received.emit(amp_l, amp_r, peak_l, peak_r)
    
    def _handle_channel_levels(self, address, *args):
        """Handle per-channel level meter data from SC.
        
        Forwarded format from SC: [slotID, ampL, ampR]
        """
        # Forwarded message has slotID at args[0], ampL at args[1], ampR at args[2]
        if len(args) >= 3:
            slot_id = int(args[0])
            amp_l = float(args[1])
            amp_r = float(args[2])
            # Debug - uncomment to verify data flow
            # print(f"CH {slot_id}: L={amp_l:.3f} R={amp_r:.3f}")
            self.channel_levels_received.emit(slot_id, amp_l, amp_r)
    
    def _handle_comp_gr(self, address, *args):
        """Handle compressor gain reduction from SC."""
        if len(args) >= 1:
            gr_db = float(args[0])
            self.comp_gr_received.emit(gr_db)
    
    def _handle_audio_devices_count(self, address, *args):
        """Handle audio device count from SC - start of device list."""
        if len(args) >= 2:
            self._audio_device_count = int(args[0])
            self._audio_device_current = str(args[1])
            self._audio_devices = []
    
    def _handle_audio_devices_item(self, address, *args):
        """Handle individual audio device from SC."""
        if len(args) >= 2:
            device_name = str(args[1])
            self._audio_devices.append(device_name)
    
    def _handle_audio_devices_done(self, address, *args):
        """Handle end of audio device list from SC."""
        self.audio_devices_received.emit(self._audio_devices, self._audio_device_current)
    
    def _handle_audio_device_changing(self, address, *args):
        """Handle notification that SC is changing audio device."""
        if len(args) >= 1:
            device_name = str(args[0])
            self.audio_device_changing.emit(device_name)
    
    def _handle_audio_device_ready(self, address, *args):
        """Handle notification that SC has finished changing device."""
        if len(args) >= 1:
            device_name = str(args[0])
            self.audio_device_ready.emit(device_name)
    
    def _handle_audio_device_error(self, address, *args):
        """Handle audio device error from SC."""
        if len(args) >= 1:
            error_msg = str(args[0])
            self.audio_device_error.emit(error_msg)
    
    def query_audio_devices(self):
        """Request list of audio devices from SC."""
        from src.config import OSC_PATHS
        if self.client:
            self.client.send_message(OSC_PATHS['audio_devices_query'], [1])
    
    def set_audio_device(self, device_name):
        """Set audio device in SC (triggers reboot)."""
        from src.config import OSC_PATHS
        if self.client:
            self.client.send_message(OSC_PATHS['audio_device_set'], [device_name])
    
    def _default_handler(self, address, *args):
        """Default handler for unknown messages."""
        # Uncomment for debugging:
        # print(f"DEFAULT: {address} {args}")
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
            except OSError:
                pass
            self.server = None
        self.client = None
        self.connected = False
    
    def disconnect(self):
        """Disconnect and clean up."""
        self._cleanup()
        logger.info("Disconnected from SuperCollider", component="OSC")
    
    def is_healthy(self):
        """Check if connection is healthy (no missed heartbeats)."""
        return self.connected and self._missed_heartbeats == 0
