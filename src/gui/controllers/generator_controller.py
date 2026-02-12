"""
GeneratorController - Handles generator slot parameter changes and OSC dispatch.

Extracted from MainFrame as Phase 3 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

from src.config import (
    CLOCK_RATE_INDEX, CUSTOM_PARAM_CONFIG, FILTER_TYPE_INDEX, GENERATORS,
    GENERATOR_PARAMS_BY_KEY, OSC_PATHS, unmap_value,
    get_generator_midi_retrig, get_generator_output_trim_db
)

# All 8 slots now use unified bus system (Phase 5: complete)
GEN_UNIFIED_SLOTS = {1, 2, 3, 4, 5, 6, 7, 8}
from src.utils.logger import logger


class GeneratorController:
    """Handles generator slot parameters and OSC dispatch."""
    
    def __init__(self, main_frame):
        self.main = main_frame
    
    def on_gate_trigger(self, slot_id):
        """Handle gate trigger from SC - flash LED."""
        slot = self.main.generator_grid.get_slot(slot_id)
        if slot:
            slot.flash_gate()
    
    def on_midi_device_changed(self, device_name):
        """Handle MIDI device selection change."""
        if self.main.osc_connected:
            if device_name:
                port_index = self.main.midi_selector.get_port_index(device_name)
                if port_index >= 0:
                    self.main.osc.client.send_message(OSC_PATHS['midi_device'], [port_index])
                    logger.info(f"MIDI device: {device_name} (port {port_index})", component="MIDI")
            else:
                self.main.osc.client.send_message(OSC_PATHS['midi_device'], [-1])
                logger.info("MIDI device: None", component="MIDI")
        
    def on_generator_param_changed(self, slot_id, param_name, value):
        """Handle per-generator parameter change.

        For slots in GEN_UNIFIED_SLOTS, routes through /noise/bus/base with
        normalized values. Otherwise uses legacy OSC paths.
        """
        if self.main.osc_connected:
            if slot_id in GEN_UNIFIED_SLOTS:
                # Unified bus system - send normalized value
                # Map param_name to unified target key
                key_map = {
                    'frequency': 'freq',
                    'cutoff': 'cutoff',
                    'resonance': 'res',
                    'attack': 'attack',
                    'decay': 'decay',
                }
                target_param = key_map.get(param_name, param_name)
                target_key = f"gen_{slot_id}_{target_param}"

                # Convert real value back to normalized (0-1)
                param_config = GENERATOR_PARAMS_BY_KEY.get(param_name)
                if param_config:
                    norm_value = unmap_value(value, param_config)
                    self.main.osc.client.send_message('/noise/bus/base', [target_key, norm_value])
            else:
                # Legacy path for non-unified slots
                path = OSC_PATHS.get(f'gen_{param_name}', f'/noise/gen/{param_name}')
                self.main.osc.client.send_message(path, [slot_id, value])
        self.main._mark_dirty()
    
    def on_generator_custom_param_changed(self, slot_id, param_index, value):
        """Handle per-generator custom parameter change.

        For slots in GEN_UNIFIED_SLOTS, routes through /noise/bus/base.
        Custom params are already 0-1 normalized.
        """
        if self.main.osc_connected:
            value = max(-1e30, min(1e30, float(value)))
            if slot_id in GEN_UNIFIED_SLOTS:
                # Unified bus system - custom params are already 0-1
                target_key = f"gen_{slot_id}_custom{param_index}"
                self.main.osc.client.send_message('/noise/bus/base', [target_key, value])
            else:
                # Legacy path for non-unified slots
                path = f"{OSC_PATHS['gen_custom']}/{slot_id}/{param_index}"
                self.main.osc.client.send_message(path, [value])
        self.main._mark_dirty()

    def on_generator_filter_changed(self, slot_id, filter_type):
        """Handle generator filter type change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_filter_type'], [slot_id, FILTER_TYPE_INDEX[filter_type]])
        self.main._mark_dirty()

    def on_generator_clock_enabled(self, slot_id, enabled):
        """Handle generator envelope ON/OFF (legacy)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_env_enabled'], [slot_id, 1 if enabled else 0])

    def on_generator_transpose(self, slot_id, semitones):
        """Send transpose to SuperCollider."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_transpose'], [slot_id, semitones])
        self.main._mark_dirty()

    def on_generator_env_source(self, slot_id, source):
        """Handle generator ENV source change (0=OFF, 1=CLK, 2=MIDI)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_env_source'], [slot_id, source])
        logger.gen(slot_id, f"env source: {['OFF', 'CLK', 'MIDI'][source]}")
        
        if self.main._midi_mode_active and not self.main._midi_mode_changing:
            self.main._deactivate_midi_mode()
        self.main._mark_dirty()

    def on_generator_clock_rate(self, slot_id, rate):
        """Handle generator clock rate change - send index."""
        rate_index = CLOCK_RATE_INDEX.get(rate, 3)
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_clock_rate'], [slot_id, rate_index])
        logger.gen(slot_id, f"rate: {rate} (index {rate_index})")
        self.main._mark_dirty()

    def on_generator_mute(self, slot_id, muted):
        """Handle generator mute from slot button."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_mute'], [slot_id, 1 if muted else 0])
        logger.gen(slot_id, f"mute: {muted}")
    
    def on_generator_midi_channel(self, slot_id, channel):
        """Handle generator MIDI channel change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_midi_channel'], [slot_id, channel])
        logger.gen(slot_id, f"MIDI channel: {channel}")

    def on_generator_portamento(self, slot_id, value):
        """Handle portamento knob change - send normalized value via OSC."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_portamento'], [slot_id, value])
        logger.gen(slot_id, f"portamento: {value:.3f}")
        self.main._mark_dirty()

    def on_generator_analog_enable(self, slot_id, enabled):
        """Handle analog stage enable/disable."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_analog_enable'], [slot_id, enabled])
        logger.gen(slot_id, f"analog enable: {enabled}")
        self.main._mark_dirty()

    def on_generator_analog_type(self, slot_id, type_index):
        """Handle analog stage type change (0=CLEAN, 1=TAPE, 2=TUBE, 3=FOLD)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_analog_type'], [slot_id, type_index])
        logger.gen(slot_id, f"analog type: {type_index}")
        self.main._mark_dirty()

    def on_generator_selected(self, slot_id):
        """Handle generator slot selection (legacy click handler)."""
        pass
    
    def on_generator_changed(self, slot_id, new_type):
        """Handle generator type change from CycleButton."""
        # P0 safety: disable hardware send before swapping generator
        # Prevents lingering synths routing stale audio to hardware outputs
        if self.main.telemetry_controller is not None:
            self.main.telemetry_controller.disable_hardware_send(slot_id - 1)

        # MOLTI-SAMP: unload buffers when switching away from any MOLTI variant
        slot = self.main.generator_grid.get_slot(slot_id)
        if slot and slot.molti_path and "MOLTI" not in new_type.upper():
            self._molti_unload(slot_id)

        synth_name = GENERATORS.get(new_type)

        self.main.generator_grid.set_generator_type(slot_id, new_type)
        
        if synth_name:
            if self.main.osc_connected:
                self.main.osc.client.send_message(OSC_PATHS['start_generator'], [slot_id, synth_name])
                midi_retrig = 1 if get_generator_midi_retrig(new_type) else 0
                self.main.osc.client.send_message(OSC_PATHS['midi_retrig'], [slot_id, midi_retrig])
                trim_db = get_generator_output_trim_db(new_type)
                self.main.osc.client.send_message(OSC_PATHS['gen_trim'], [slot_id, trim_db])
                self._sync_strip_state_to_sc(slot_id)
                self._sync_generator_slot_state_to_sc(slot_id)
            
            self.main.generator_grid.set_generator_active(slot_id, True)
            slot = self.main.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(True)
            self.main.active_generators[slot_id] = synth_name
            self.main.mixer_panel.set_channel_active(slot_id, True)
        else:
            if self.main.osc_connected:
                self.main.osc.client.send_message(OSC_PATHS['stop_generator'], [slot_id])
                self.main.osc.client.send_message(OSC_PATHS['midi_retrig'], [slot_id, 0])
            
            self.main.generator_grid.set_generator_active(slot_id, False)
            slot = self.main.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(False)
            if slot_id in self.main.active_generators:
                del self.main.active_generators[slot_id]
            self.main.mixer_panel.set_channel_active(slot_id, False)
        self.main._mark_dirty()

    def _sync_strip_state_to_sc(self, slot_id):
        """Re-sync mixer strip state to SC after generator change."""
        if not self.main.osc_connected:
            return
        
        state = self.main.mixer_panel.get_channel_strip_state(slot_id)
        if not state:
            return
        
        self.main.osc.client.send_message(OSC_PATHS['gen_pan'], [slot_id, state['pan']])
        self.main.osc.client.send_message(OSC_PATHS['gen_mute'], [slot_id, 1 if state['muted'] else 0])
        self.main.osc.client.send_message(OSC_PATHS['gen_strip_solo'], [slot_id, 1 if state['soloed'] else 0])
        self.main.osc.client.send_message(OSC_PATHS['gen_gain'], [slot_id, state['gain_db']])
        
        for band in ['lo', 'mid', 'hi']:
            osc_path = f"{OSC_PATHS['gen_strip_eq_base']}/{band}"
            self.main.osc.client.send_message(osc_path, [slot_id, state[f'eq_{band}']])
        
        logger.debug(f"Gen {slot_id} strip state synced (pan={state['pan']:.2f})", component="OSC")
    
    def _sync_generator_slot_state_to_sc(self, slot_id):
        """Re-sync generator slot control state to SC after type change."""
        if not self.main.osc_connected:
            return
        
        slot = self.main.generator_grid.get_slot(slot_id)
        if not slot:
            return
        
        if slot.muted:
            self.main.osc.client.send_message(OSC_PATHS['gen_mute'], [slot_id, 1])
        
        self.main.osc.client.send_message(OSC_PATHS['gen_env_source'], [slot_id, slot.env_source])
        
        if slot.env_source == 1 and hasattr(slot, 'rate_btn'):
            rate = slot.rate_btn.get_value()
            rate_index = CLOCK_RATE_INDEX.get(rate, 3)
            self.main.osc.client.send_message(OSC_PATHS['gen_clock_rate'], [slot_id, rate_index])
        
        if slot.env_source == 2:
            self.main.osc.client.send_message(OSC_PATHS['gen_midi_channel'], [slot_id, slot.midi_channel])
        
        if hasattr(slot, 'filter_btn'):
            filter_type = slot.filter_btn.get_value()
            self.main.osc.client.send_message(OSC_PATHS['gen_filter_type'], [slot_id, FILTER_TYPE_INDEX[filter_type]])
        
        logger.debug(f"Gen {slot_id} slot state synced (mute={slot.muted}, env={slot.env_source})", component="OSC")

    # =========================================================================
    # MOLTI-SAMP: Load / Unload
    # =========================================================================

    def _get_molti_loader(self):
        """Lazy-init the shared MoltiLoader and MoltiBufPool."""
        if not hasattr(self, '_molti_loader'):
            from src.audio.molti_buf_pool import MoltiBufPool
            from src.audio.molti_loader import MoltiLoader
            self._molti_pool = MoltiBufPool()
            self._molti_loader = None  # Created when osc is available
        if self._molti_loader is None and self.main.osc_connected:
            from src.audio.molti_loader import MoltiLoader
            from pythonosc import udp_client
            from src.config import OSC_HOST, SC_SERVER_PORT
            sc_server_client = udp_client.SimpleUDPClient(OSC_HOST, SC_SERVER_PORT)
            self._molti_loader = MoltiLoader(sc_server_client, self._molti_pool)
        return self._molti_loader

    def on_molti_load_requested(self, slot_id):
        """Handle MOLTI-SAMP LOAD button click — open file dialog and load."""
        from PyQt5.QtWidgets import QFileDialog
        from pathlib import Path

        slot = self.main.generator_grid.get_slot(slot_id)
        if not slot:
            return

        # Check if a recent file was selected via right-click menu
        filepath = getattr(slot, '_molti_recent_path', None)
        slot._molti_recent_path = None

        if not filepath:
            # Open file dialog
            start_dir = str(Path.home())
            if slot.molti_path:
                start_dir = str(Path(slot.molti_path).parent)
            filepath, _ = QFileDialog.getOpenFileName(
                self.main,
                "Load Multisample",
                start_dir,
                "Korg Multisample (*.korgmultisample);;All Files (*)",
            )

        if not filepath:
            return

        self._do_molti_load(slot_id, filepath)

    def _do_molti_load(self, slot_id, filepath):
        """Execute multisample load (sync, sleep-based — interim)."""
        if not self.main.osc_connected:
            logger.warning("Cannot load multisample: not connected to SC", component="MOLTI")
            return

        # Ensure bufBus indices are available
        buf_bus_idx = self.main.osc.get_buf_bus_index(slot_id - 1)
        if buf_bus_idx < 0:
            # Query SC and retry after brief wait
            self.main.osc.query_buf_buses()
            logger.info("[MOLTI] Querying bufBus indices from SC...", component="MOLTI")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(300, lambda: self._do_molti_load_retry(slot_id, filepath))
            return

        self._do_molti_load_now(slot_id, filepath, buf_bus_idx)

    def _do_molti_load_retry(self, slot_id, filepath):
        """Retry load after bufBus query response."""
        buf_bus_idx = self.main.osc.get_buf_bus_index(slot_id - 1)
        if buf_bus_idx < 0:
            logger.error("[MOLTI] bufBus index unavailable — cannot load", component="MOLTI")
            slot = self.main.generator_grid.get_slot(slot_id)
            if slot:
                slot.molti_name_label.setText("NO BUFBUS")
            return
        self._do_molti_load_now(slot_id, filepath, buf_bus_idx)

    def _do_molti_load_now(self, slot_id, filepath, buf_bus_idx):
        """Load multisample synchronously (brief UI freeze — interim)."""
        loader = self._get_molti_loader()
        if not loader:
            logger.error("[MOLTI] Loader unavailable — not connected", component="MOLTI")
            return

        slot = self.main.generator_grid.get_slot(slot_id)
        if slot:
            slot.molti_load_btn.setEnabled(False)
            slot.molti_name_label.setText("loading...")

        try:
            result = loader.load(
                slot=slot_id - 1,
                filepath=filepath,
                buf_bus_index=buf_bus_idx,
            )
            if slot:
                slot.molti_load_btn.setEnabled(True)
                slot.set_molti_loaded(result['name'], filepath)
            logger.info(
                f"[MOLTI] Slot {slot_id}: loaded '{result['name']}' "
                f"({result['zone_count']} zones, {result['mapped_notes']}/128 notes)",
                component="MOLTI"
            )
            from src.config.molti_recent import add_recent_file
            add_recent_file(filepath)
            self.main._mark_dirty()
        except Exception as e:
            logger.error(f"[MOLTI] Load failed: {e}", component="MOLTI")
            if slot:
                slot.molti_load_btn.setEnabled(True)
                slot.set_molti_unloaded()
                slot.molti_name_label.setText("LOAD FAILED")

    def molti_reload_all(self):
        """Re-load all MOLTI-SAMP slots that have a saved path.

        Called after reconnect when SC has lost all buffers/tables.
        Also resets the loader so it uses the new osc.client.
        """
        # Reset loader to pick up new osc.client after reconnect
        if hasattr(self, '_molti_loader'):
            self._molti_loader = None

        for slot_id in range(1, 9):
            slot = self.main.generator_grid.get_slot(slot_id)
            if slot and slot.molti_path and "MOLTI" in slot.generator_type.upper():
                logger.info(f"[MOLTI] Reconnect: re-loading slot {slot_id}", component="MOLTI")
                self._do_molti_load(slot_id, slot.molti_path)

    def _molti_unload(self, slot_id, _retry=0):
        """Unload multisample from a slot (called on type change away from MOLTI-SAMP).

        Always resets bufBus to [-1,-1,0,0]. If bufBus index is unknown,
        queries SC and retries via QTimer (no UI thread blocking).
        """
        loader = self._get_molti_loader()
        if not loader or not self.main.osc_connected:
            return

        buf_bus_idx = self.main.osc.get_buf_bus_index(slot_id - 1)
        if buf_bus_idx < 0 and _retry < 3:
            if _retry == 0:
                self.main.osc.query_buf_buses()
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(150, lambda: self._molti_unload(slot_id, _retry + 1))
            return

        loader.unload(slot_id - 1, buf_bus_idx if buf_bus_idx >= 0 else None)
        if buf_bus_idx < 0:
            logger.warning(
                f"[MOLTI] Unloaded slot {slot_id} without bufBus reset "
                "(indices unavailable after {_retry} retries)",
                component="MOLTI"
            )
