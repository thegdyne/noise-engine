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
from pythonosc.osc_bundle_builder import OscBundleBuilder, IMMEDIATELY
from pythonosc.osc_message_builder import OscMessageBuilder
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QCoreApplication

from src.utils.logger import logger


class OSCBridge(QObject):
    """Manages OSC communication with SuperCollider."""

    # Signals for thread-safe notifications
    gate_triggered = pyqtSignal(int)  # slot_id
    levels_received = pyqtSignal(float, float, float, float)  # ampL, ampR, peakL, peakR
    midi_cc_received = pyqtSignal(int, int, int)  # channel, cc, value
    channel_levels_received = pyqtSignal(int, float, float)  # slot_id, ampL, ampR
    comp_gr_received = pyqtSignal(float)  # compressor gain reduction in dB
    mod_bus_value_received = pyqtSignal(int, float)  # bus_idx, value (for mod scope)
    mod_values_received = pyqtSignal(list)  # [(slot, param, value), ...] for slider visualization
    extmod_values_received = pyqtSignal(list)  # [(target_str, value), ...] for extended mod visualization
    bus_values_received = pyqtSignal(list)  # [(targetKey, value), ...] for unified bus system visualization
    connection_lost = pyqtSignal()  # Emitted when heartbeat fails
    connection_lost_reason = pyqtSignal(str)  # Reason: "heartbeat_missed", "ping_timeout", etc.
    connection_restored = pyqtSignal()  # Emitted when reconnect succeeds
    # Scope tap signals
    scope_data_received = pyqtSignal(object)  # numpy array of floats
    scope_debug_done_received = pyqtSignal(str)  # SC csv path
    # Telemetry signals (development tool)
    telem_data_received = pyqtSignal(int, object)      # slot, data dict
    telem_waveform_received = pyqtSignal(int, object)   # slot, samples tuple
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
        self._last_verify_fail = None

        # Heartbeat timer
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._check_heartbeat)

        # Store connection params for reconnect
        self._host = None
        self._port = None

        # Flag to prevent signal emission after deletion
        # Only shutdown() sets this True - disconnect() does NOT
        self._deleted = False
        self._shutdown = False
        self._connecting = False  # Guard against re-entrant connect()

    def shutdown(self):
        """Stop the OSC bridge completely."""
        # Notify SC that Python is quitting so it stops sending messages
        if self.client:
            try:
                self.client.send_message('/noise/quit', [])
            except Exception:
                pass  # Best effort - SC may already be gone
        self._shutdown = True
        self._deleted = True  # Only shutdown sets this
        self._cleanup()

    def connect(self, host=None, port=None):
        """Connect to SuperCollider with verification."""
        from src.config import OSC_HOST, OSC_SEND_PORT

        # Guard against re-entrant connect (can happen via processEvents in verify loop)
        if self._connecting:
            logger.warning("connect() already in progress", component="OSC")
            return False
        self._connecting = True

        # Reconnect-safe: disconnect() should not permanently suppress handlers
        self._shutdown = False
        self._deleted = False

        # Handle already-connected case (e.g., double-click, UI bug)
        # Use join_thread=False to avoid 0.2s hiccup during reconnect
        if self.connected:
            logger.warning("connect() called while already connected; reconnecting", component="OSC")
            self._cleanup(join_thread=False)
        else:
            self._cleanup(join_thread=False)

        self._host = host or OSC_HOST
        self._port = port or OSC_SEND_PORT

        try:
            # Start receiver first (to catch pong)
            if not self._start_server():
                logger.error("OSC receive server failed to start; cannot connect", component="OSC")
                self._cleanup(join_thread=False)
                return False

            # Create client
            self.client = udp_client.SimpleUDPClient(self._host, self._port)

            # Verify connection with ping
            if not self._verify_connection():
                reason = self._last_verify_fail or "unknown"  # Read BEFORE cleanup
                self._cleanup(join_thread=True)
                if not (self._shutdown or self._deleted):
                    self.connection_lost_reason.emit(reason)

                if reason == "ping_timeout":
                    logger.error(f"SuperCollider not responding on port {self._port}", component="OSC")
                    logger.info("Check: NetAddr.langPort.postln; in SC", component="OSC")
                else:
                    logger.info(f"Connect aborted ({reason})", component="OSC")

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
            self._cleanup(join_thread=False)
            return False
        finally:
            self._connecting = False

    def _verify_connection(self):
        """Send ping and wait for pong response."""
        from src.config import OSC_PATHS

        self._ping_received = False

        # Send ping
        self.client.send_message(OSC_PATHS['ping'], [1])

        # Wait for pong (blocking with timeout)
        # Use monotonic time to avoid clock-jump issues during sleep/wake
        start_time = time.monotonic()
        timeout_sec = self.PING_TIMEOUT_MS / 1000.0

        self._last_verify_fail = None

        while not self._ping_received:
            # Abort if connect was cancelled (e.g., user clicked disconnect)
            if self._shutdown or self._deleted or not self._connecting:
                self._last_verify_fail = "cancelled"
                return False
            if time.monotonic() - start_time > timeout_sec:
                self._last_verify_fail = "ping_timeout"
                return False
            # Keep UI responsive if connect() is called from the GUI thread
            QCoreApplication.processEvents()
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
            # Log every miss so users/devs can see pattern before loss
            logger.debug(f"Missed heartbeat {self._missed_heartbeats}/{self.HEARTBEAT_MISS_LIMIT}", component="OSC")
            if self._missed_heartbeats >= self.HEARTBEAT_MISS_LIMIT:
                logger.error(f"CONNECTION LOST - {self.HEARTBEAT_MISS_LIMIT} missed heartbeats", component="OSC")
                # Full teardown to avoid zombie connection state
                self.disconnect()
                self.connection_lost_reason.emit("heartbeat_missed")
                self.connection_lost.emit()
                return
        else:
            # Got response, reset counter
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
        # Note: connect() calls _cleanup() internally, no need to duplicate
        time.sleep(0.05)  # Brief pause before reconnect attempt

        if self.connect(self._host, self._port):
            self.connection_restored.emit()
            return True
        return False

    def _start_server(self):
        """Start OSC server to receive messages from SC."""
        from src.config import OSC_RECEIVE_PORT, OSC_PATHS

        # Guard: if server already running, don't start another
        if (
                self.server
                and self.server_thread
                and self.server_thread.is_alive()
                and getattr(self.server, "socket", None)
        ):
            return True

        dispatcher = Dispatcher()

        # Connection management
        dispatcher.map(OSC_PATHS['pong'], self._handle_pong)
        dispatcher.map(OSC_PATHS['heartbeat_ack'], self._handle_heartbeat_ack)

        # Handle gate triggers from SC
        dispatcher.map(OSC_PATHS['midi_gate'], self._handle_gate)

        # Handle MIDI CC from SC (SSOT: use OSC_PATHS)
        dispatcher.map(OSC_PATHS['midi_cc'], self._handle_midi_cc)

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

        # Handle mod bus values from SC (for scope display)
        dispatcher.map(OSC_PATHS['mod_bus_value'], self._handle_mod_bus_value)
        dispatcher.map(OSC_PATHS['extmod_values'], self._handle_extmod_values)

        # Handle batched mod values from SC (for slider visualization) (SSOT: use OSC_PATHS)
        dispatcher.map(OSC_PATHS['mod_values'], self._handle_mod_values)

        # Handle unified bus values from SC (for generator slider visualization)
        dispatcher.map(OSC_PATHS['bus_values'], self._handle_bus_values)

        # Handle scope tap waveform data from SC
        dispatcher.map(OSC_PATHS['scope_data'], self._handle_scope_data)

        # Handle scope debug capture completion from SC
        dispatcher.map(OSC_PATHS['scope_debug_done'], self._handle_scope_debug_done)

        # Telemetry (development tool)
        dispatcher.map(OSC_PATHS['telem_gen'], self._handle_telem_gen)
        dispatcher.map(OSC_PATHS['telem_wave'], self._handle_telem_wave)

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
            return True
        except Exception as e:
            logger.warning(f"Could not start OSC receive server: {e}", component="OSC")
            self.server = None
            self.server_thread = None
            return False

    def _handle_pong(self, address, *args):
        """Handle pong response from SC."""
        self._ping_received = True

    def _handle_heartbeat_ack(self, address, *args):
        """Handle heartbeat acknowledgment from SC."""
        self._heartbeat_received = True

    def _handle_gate(self, address, *args):
        """Handle gate trigger from SC - emit signal for thread safety."""
        if self._shutdown or self._deleted:
            return
        if len(args) > 0:
            slot_id = int(args[0])
            self.gate_triggered.emit(slot_id)

    def _handle_midi_cc(self, address, *args):
        """Handle MIDI CC from SC."""
        if self._shutdown or self._deleted:
            return
        if len(args) >= 3:
            channel = int(args[0])
            cc = int(args[1])
            value = int(args[2])
            self.midi_cc_received.emit(channel, cc, value)

    def _handle_levels(self, address, *args):
        """Handle level meter data from SC."""
        if self._shutdown or self._deleted:
            return
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
        if self._shutdown or self._deleted:
            return
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
        if self._shutdown or self._deleted:
            return
        if len(args) >= 1:
            gr_db = float(args[0])
            self.comp_gr_received.emit(gr_db)

    def _handle_mod_bus_value(self, address, *args):
        """Handle mod bus value from SC (for scope display)."""
        if self._shutdown or self._deleted:
            return
        if len(args) >= 2:
            bus_idx = int(args[0])
            value = float(args[1])
            self.mod_bus_value_received.emit(bus_idx, value)

    def _handle_mod_values(self, address, *args):
        """Handle batched modulated parameter values from SC (for slider visualization).

        Format: [slot1, param1, val1, slot2, param2, val2, ...]
        Emits: [(slot, param, value), ...]
        """
        if self._shutdown or self._deleted:
            return

        # Parse triplets
        values = []
        i = 0
        while i + 2 < len(args):
            slot = int(args[i])
            param = str(args[i + 1])
            value = float(args[i + 2])
            values.append((slot, param, value))
            i += 3

        if values:
            self.mod_values_received.emit(values)

    def _handle_audio_devices_count(self, address, *args):
        """Handle audio device count from SC - start of device list."""
        if len(args) >= 2:
            self._audio_device_count = int(args[0])
            self._audio_device_current = str(args[1])
            self._audio_devices = []

    def _handle_audio_devices_item(self, address, *args):
        """Handle individual audio device from SC.

        Handles both [idx, name] and [name] formats defensively.
        """
        if len(args) >= 2:
            # Format: [idx, name]
            self._audio_devices.append(str(args[1]))
        elif len(args) == 1:
            # Format: [name] only
            self._audio_devices.append(str(args[0]))

    def _handle_audio_devices_done(self, address, *args):
        """Handle end of audio device list from SC."""
        if self._shutdown or self._deleted:
            return
        # Validate we received expected number of devices
        if self._audio_device_count and len(self._audio_devices) != self._audio_device_count:
            logger.warning(
                f"Audio devices list size mismatch: expected {self._audio_device_count}, got {len(self._audio_devices)}",
                component="OSC",
            )
        self.audio_devices_received.emit(self._audio_devices, self._audio_device_current)

    def _handle_audio_device_changing(self, address, *args):
        """Handle notification that SC is changing audio device."""
        if self._shutdown or self._deleted:
            return
        if len(args) >= 1:
            device_name = str(args[0])
            self.audio_device_changing.emit(device_name)

    def _handle_audio_device_ready(self, address, *args):
        """Handle notification that SC has finished changing device."""
        if self._shutdown or self._deleted:
            return
        if len(args) >= 1:
            device_name = str(args[0])
            self.audio_device_ready.emit(device_name)

    def _handle_audio_device_error(self, address, *args):
        """Handle audio device error from SC."""
        if self._shutdown or self._deleted:
            return
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


    # New handler (matching existing pattern):
    def _handle_extmod_values(self, address, *args):
        """Handle batched extended mod values from SC (for UI visualization).
        Format: [targetStr1, val1, targetStr2, val2, ...]
        Emits: [(target_str, value), ...]
        """
        if self._shutdown or self._deleted:
            return
        # Parse pairs
        values = []
        i = 0
        while i + 1 < len(args):
            target_str = str(args[i])
            value = float(args[i + 1])
            values.append((target_str, value))
            i += 2
        if values:
            self.extmod_values_received.emit(values)

    def _handle_bus_values(self, address, *args):
        """Handle batched unified bus values from SC (for generator slider visualization).
        Format: [targetKey1, normalizedVal1, targetKey2, normalizedVal2, ...]
        Emits: [(targetKey, normalizedValue), ...]

        These are pre-normalized 0-1 values from the unified bus system.
        The modulation controller will apply curve-aware denormalization for display.
        """
        if self._shutdown or self._deleted:
            return
        # Parse pairs
        values = []
        i = 0
        while i + 1 < len(args):
            target_key = str(args[i])
            norm_value = float(args[i + 1])
            values.append((target_key, norm_value))
            i += 2
        if values:
            self.bus_values_received.emit(values)

    def _handle_scope_data(self, address, *args):
        """Handle scope waveform data from SC (1024 floats)."""
        if self._shutdown or self._deleted:
            return
        if len(args) > 0:
            self.scope_data_received.emit(args)

    def _handle_scope_debug_done(self, address, *args):
        """Handle scope debug capture completion from SC."""
        if self._shutdown or self._deleted:
            return
        sc_path = str(args[0]) if len(args) > 0 else ""
        self.scope_debug_done_received.emit(sc_path)

    def _handle_telem_gen(self, address, *args):
        """Handle /noise/telem/gen from SC.

        Args: [slot, freq, phase, p0, p1, p2, p3, p4, rms1, rms2, rms3, peak, badValue]
        """
        if self._shutdown or self._deleted:
            return
        if len(args) < 12:
            return
        slot = int(args[0])
        data = {
            'slot': slot,
            'freq': float(args[1]),
            'phase': float(args[2]),
            'p0': float(args[3]),
            'p1': float(args[4]),
            'p2': float(args[5]),
            'p3': float(args[6]),
            'p4': float(args[7]),
            'rms_stage1': float(args[8]),
            'rms_stage2': float(args[9]),
            'rms_stage3': float(args[10]),
            'peak': float(args[11]),
            'bad_value': int(args[12]) if len(args) > 12 else 0,
        }
        self.telem_data_received.emit(slot, data)

    def _handle_telem_wave(self, address, *args):
        """Handle /noise/telem/wave from SC.

        Args: [slot, ...128 samples]
        """
        if self._shutdown or self._deleted:
            return
        if len(args) < 2:
            return
        slot = int(args[0])
        self.telem_waveform_received.emit(slot, args[1:])

    def send(self, path_key, args):
        """Send OSC message using SSOT path key.

        Args:
            path_key: Key from OSC_PATHS dict (e.g., 'master_volume')
            args: List of arguments to send
        """
        from src.config import OSC_PATHS

        # Silent ignore during shutdown or mid-connect
        if self._shutdown or self._deleted or self._connecting:
            return

        # Warn user (rate-limited) if not connected - prevents "nothing happened" confusion
        # Also emit connection_lost so UI can show recovery prompt
        if not self.client or not self.connected:
            now = time.monotonic()
            last_warn = getattr(self, "_last_send_fail_ts", 0.0)
            last_emit = getattr(self, "_last_disconnected_emit_ts", 0.0)

            if now - last_warn > 2.0:
                logger.warning("OSC send ignored: not connected", component="OSC")
                self._last_send_fail_ts = now

            if now - last_emit > 2.0:
                self.connection_lost_reason.emit("send_while_disconnected")
                self.connection_lost.emit()
                self._last_disconnected_emit_ts = now

            return

        path = OSC_PATHS.get(path_key)
        if not path:
            logger.error(f"Unknown OSC path_key: {path_key}", component="OSC")
            return

        try:
            self.client.send_message(path, args)
        except Exception as e:
            logger.warning(f"OSC send failed ({path_key}): {e}", component="OSC")

    def send_bundle(self, messages):
        """Send multiple OSC messages as an atomic bundle (Pillar 2).

        All messages execute in the same SuperCollider audio block,
        preventing audio dropout during generator swaps.

        Args:
            messages: List of (path, args) tuples, e.g.:
                [('/s_new', ['synthName', 1001, 1, 100]),
                 ('/n_free', [1000])]
        """
        if self._shutdown or self._deleted or self._connecting:
            return

        if not self.client or not self.connected:
            logger.warning("OSC bundle ignored: not connected", component="OSC")
            return

        try:
            bundle = OscBundleBuilder(IMMEDIATELY)
            for path, args in messages:
                msg = OscMessageBuilder(address=path)
                for arg in args:
                    msg.add_arg(arg)
                bundle.add_content(msg.build())
            self.client.send(bundle.build())
        except Exception as e:
            logger.warning(f"OSC bundle send failed: {e}", component="OSC")

    def _cleanup(self, join_thread=True):
        """Clean up connection resources.

        Args:
            join_thread: If True, wait for server thread to terminate (may block up to 0.2s).
                         Use False during reconnect to avoid visible hiccup.
        """
        self._heartbeat_timer.stop()

        # Reset protocol state to avoid stale flags on reconnect
        self._ping_received = False
        self._heartbeat_received = False
        self._missed_heartbeats = 0
        self._last_verify_fail = None

        if self.server:
            try:
                self.server.shutdown()
                # Release the socket so port can be rebound
                self.server.server_close()
            except Exception as e:
                logger.debug(f"OSC server cleanup: {e}", component="OSC")
            self.server = None

        # Join server thread to ensure clean termination
        # Guard against calling from server thread itself
        # Skip join if join_thread=False (non-blocking reconnect)
        if join_thread and self.server_thread and self.server_thread.is_alive():
            if threading.current_thread() is not self.server_thread:
                self.server_thread.join(timeout=0.2)
        self.server_thread = None

        self.client = None
        self.connected = False

    def disconnect(self):
        """Disconnect and clean up (allows reconnect later)."""
        # NOTE: Do NOT set _deleted here - that prevents reconnect from working
        # Only shutdown() sets _deleted=True
        self._connecting = False  # Reset in case disconnect called during connect
        self._cleanup()
        logger.info("Disconnected from SuperCollider", component="OSC")

    def is_healthy(self):
        """Check if connection is healthy (no missed heartbeats)."""
        return self.connected and self._missed_heartbeats == 0