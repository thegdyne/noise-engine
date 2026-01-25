"""
ConnectionController - Handles SuperCollider connection lifecycle.

Extracted from MainFrame as Phase 5 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

from src.config import OSC_PATHS
from src.gui.theme import COLORS
from src.gui.crossmod_osc_bridge import CrossmodOSCBridge
from src.utils.logger import logger


class ConnectionController:
    """Handles SuperCollider connection lifecycle."""
    
    def __init__(self, main_frame):
        self.main = main_frame

    def _try_auto_connect(self):
        """Attempt auto-connect once."""
        self.main.connect_btn.setEnabled(True)
        if not self.main.osc_connected:
            self.toggle_connection()

    def _sc_is_ready(self):
        """Check if SC ready.json exists and is fresh (< 60s old)."""
        import os as _os
        import time as _time
        import json as _json
        ready_path = _os.path.expanduser("~/Library/Application Support/NoiseEngine/state/ready.json")
        try:
            if _os.path.exists(ready_path):
                age = _time.time() - _os.path.getmtime(ready_path)
                if age < 60:
                    with open(ready_path) as f:
                        data = _json.load(f)
                    return data.get("status") == "ready"
        except Exception as e:
            from src.utils.logger import logger
            logger.debug(f"SC ready check failed: {e}", component="OSC")
        return False

    def toggle_connection(self):
        """Connect/disconnect to SuperCollider."""
        if not self.main.osc_connected:
            # Connect signals before connecting
            self.main.osc.gate_triggered.connect(self.main.generator.on_gate_trigger)
            self.main.osc.levels_received.connect(self.main.master.on_levels_received)
            self.main.osc.channel_levels_received.connect(self.main.master.on_channel_levels_received)
            self.main.osc.connection_lost.connect(self.on_connection_lost)
            self.main.osc.connection_restored.connect(self.on_connection_restored)
            self.main.osc.audio_devices_received.connect(self.main.master.on_audio_devices_received)
            self.main.osc.audio_device_changing.connect(self.main.master.on_audio_device_changing)
            self.main.osc.audio_device_ready.connect(self.main.master.on_audio_device_ready)
            self.main.osc.comp_gr_received.connect(self.main.master.on_comp_gr_received)
            self.main.osc.mod_bus_value_received.connect(self.main.modulation.on_mod_bus_value)
            self.main.osc.mod_values_received.connect(self.main.modulation.on_mod_values_received)
            self.main.osc.extmod_values_received.connect(self.main.modulation.on_extmod_values_received)
            self.main.osc.bus_values_received.connect(self.main.modulation.on_bus_values_received)
            if self.main.osc.connect():
                self.main.osc_connected = True
                # Initialize crossmod OSC bridge
                if self.main.crossmod_osc is None:
                    self.main.crossmod_osc = CrossmodOSCBridge(self.main.crossmod_state, self.main.osc.client)
                self.main._set_header_buttons_enabled(True)
                self.main.master_section.set_osc_bridge(self.main.osc)
                self.main.inline_fx.set_osc_bridge(self.main.osc)
                self.main.inline_fx.sync_state()
                if self.main.fx_window:
                    self.main.fx_window.set_osc_bridge(self.main.osc)
                self.main.connect_btn.setText("Disconnect")
                self.main.status_label.setText("Connected")
                self.main.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
                
                self.main.osc.client.send_message(OSC_PATHS['clock_bpm'], [self.main.master_bpm])
                
                # Send initial master volume
                self.main.osc.client.send_message(OSC_PATHS['master_volume'], [self.main.master_section.get_volume()])
                
                # Query audio devices
                self.main.osc.query_audio_devices()

                # Send current MIDI device if one is selected
                current_midi = self.main.midi_selector.get_current_device()
                logger.info(f"MIDI device at connect: {current_midi!r}", component="OSC")
                if current_midi:
                    port_index = self.main.midi_selector.get_port_index(current_midi)
                    logger.info(f"MIDI port index: {port_index}", component="OSC")
                    if port_index >= 0:
                        self.main.osc.client.send_message(OSC_PATHS['midi_device'], [port_index])
                
                # Send initial mod source state
                self.main.modulation._sync_mod_sources()
            else:
                self.main.status_label.setText("Connection Failed")
                self.main.status_label.setStyleSheet(f"color: {COLORS['warning_text']};")
        else:
            try:
                # Disconnect all signals connected in toggle_connection
                self.main.osc.gate_triggered.disconnect(self.main.generator.on_gate_trigger)
                self.main.osc.levels_received.disconnect(self.main.master.on_levels_received)
                self.main.osc.channel_levels_received.disconnect(self.main.master.on_channel_levels_received)
                self.main.osc.connection_lost.disconnect(self.on_connection_lost)
                self.main.osc.connection_restored.disconnect(self.on_connection_restored)
                self.main.osc.audio_devices_received.disconnect(self.main.master.on_audio_devices_received)
                self.main.osc.audio_device_changing.disconnect(self.main.master.on_audio_device_changing)
                self.main.osc.audio_device_ready.disconnect(self.main.master.on_audio_device_ready)
                self.main.osc.comp_gr_received.disconnect(self.main.master.on_comp_gr_received)
                self.main.osc.mod_bus_value_received.disconnect(self.main.modulation.on_mod_bus_value)
                self.main.osc.mod_values_received.disconnect(self.main.modulation.on_mod_values_received)
                self.main.osc.extmod_values_received.disconnect(self.main.modulation.on_extmod_values_received)
                self.main.osc.bus_values_received.disconnect(self.main.modulation.on_bus_values_received)
            except TypeError:
                pass  # Signals weren't connected
            self.main.osc.disconnect()
            self.main.osc_connected = False
            self.main._set_header_buttons_enabled(False)
            self.main.connect_btn.setText("Connect SuperCollider")
            self.main.status_label.setText("Disconnected")
            self.main.status_label.setStyleSheet(f"color: {COLORS['submenu_text']};")
    
    def on_connection_lost(self):
        """Handle connection lost - show prominent warning."""
        self.main.osc_connected = False
        self.main._set_header_buttons_enabled(False)
        self.main.connect_btn.setText("RECONNECT")
        self.main.connect_btn.setStyleSheet(f"background-color: {COLORS['warning_text']}; color: black; font-weight: bold;")
        self.main.status_label.setText("CONNECTION LOST")
        self.main.status_label.setStyleSheet(f"color: {COLORS['warning_text']}; font-weight: bold;")
    
    def on_connection_restored(self):
        """Handle connection restored after reconnect."""
        self.main.osc_connected = True
        self.main._set_header_buttons_enabled(True)
        self.main.master_section.set_osc_bridge(self.main.osc)
        self.main.inline_fx.set_osc_bridge(self.main.osc)
        self.main.inline_fx.sync_state()
        if self.main.fx_window:
            self.main.fx_window.set_osc_bridge(self.main.osc)
        self.main.connect_btn.setText("Disconnect")
        self.main.connect_btn.setStyleSheet(self._connect_btn_style())
        self.main.status_label.setText("Connected")
        self.main.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
        
        # Resend current state
        self.main.osc.client.send_message(OSC_PATHS['clock_bpm'], [self.main.master_bpm])

        # Clear mod routing (SC has fresh state after restart)
        self.main.mod_routing.clear()

    def _connect_btn_style(self):
        """Return the standard connect button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {COLORS['border_light']};
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['text']};
            }}
        """
