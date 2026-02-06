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
