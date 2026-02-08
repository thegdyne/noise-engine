"""
PresetController - Handles preset save/load/apply/init.

Extracted from MainFrame as Phase 1 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtGui import QKeySequence
from pathlib import Path

from src.config import OSC_PATHS
from src.presets import (
    PresetManager, PresetState, SlotState, MixerState,
    ChannelState, MasterState, ModSourcesState, FXState, FXSlotsState
)
from src.utils.logger import logger
from src.gui.controllers.modulation_controller import _build_source_key, _build_target_key


class PresetController:
    """Handles preset save/load/apply/init operations."""
    
    def __init__(self, main_frame):
        self.main = main_frame
        self.preset_manager = PresetManager()
    
    def _setup_preset_menu(self):
        """Create Preset menu in menu bar."""
        menu_bar = self.main.menuBar()
        preset_menu = menu_bar.addMenu("Preset")

        save_action = preset_menu.addAction("Save", self._save_preset)
        save_action.setShortcut(QKeySequence("Ctrl+S"))

        save_as_action = preset_menu.addAction("Save As...", self._save_preset_as)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))

        preset_menu.addSeparator()

        load_action = preset_menu.addAction("Load...", self._load_preset)
        load_action.setShortcut(QKeySequence("Ctrl+O"))

        preset_menu.addSeparator()

        init_action = preset_menu.addAction("Init (New)", self._init_preset)
        init_action.setShortcut(QKeySequence("Ctrl+N"))

    def _save_preset(self):
        """Save current state - dialog pre-fills with current preset name."""
        if self.main._current_preset_name:
            default_path = self.preset_manager.presets_dir / f"{self.main._current_preset_name}.json"
        else:
            current_name = self.main.preset_name.text()
            default_path = self.preset_manager.presets_dir / f"{current_name}.json"

        filepath, _ = QFileDialog.getSaveFileName(
            self.main,
            "Save Preset",
            str(default_path),
            "Preset Files (*.json)",
        )

        if filepath:
            if not filepath.endswith('.json'):
                filepath += '.json'
            name = Path(filepath).stem
            self._do_save_preset(name, Path(filepath))

    def _save_preset_as(self):
        """Save current state as new preset - dialog starts blank."""
        filepath, _ = QFileDialog.getSaveFileName(
            self.main,
            "Save Preset As",
            str(self.preset_manager.presets_dir),
            "Preset Files (*.json)",
        )

        if filepath:
            if not filepath.endswith('.json'):
                filepath += '.json'
            name = Path(filepath).stem
            self._do_save_preset(name, Path(filepath))

    def _do_save_preset(self, name: str, filepath):
        """Internal: actually save the preset to the specified filepath."""
        from src.config import get_current_pack
        from src.presets.preset_schema import PRESET_VERSION
        from datetime import datetime

        slots = []
        for slot_id in range(1, 9):
            slot_widget = self.main.generator_grid.slots[slot_id]
            slot_dict = slot_widget.get_state()
            # Inject ARP settings from arp_manager
            if hasattr(self.main, 'keyboard') and hasattr(self.main.keyboard, 'arp_manager'):
                engine = self.main.keyboard.arp_manager.get_engine(slot_id - 1)
                arp = engine.get_settings()
                slot_dict["arp_enabled"] = arp.enabled
                slot_dict["arp_rate"] = arp.rate_index
                slot_dict["arp_pattern"] = list(type(arp.pattern)).index(arp.pattern)
                slot_dict["arp_octaves"] = arp.octaves
                slot_dict["arp_hold"] = arp.hold
            # Inject SEQ settings from motion_manager
            if hasattr(self.main, 'keyboard') and hasattr(self.main.keyboard, 'motion_manager'):
                from src.model.sequencer import StepType, PlayMode, MotionMode
                mm = self.main.keyboard.motion_manager
                seq_engine = mm.get_seq_engine(slot_id - 1)
                if seq_engine is not None:
                    seq = seq_engine.get_settings()
                    step_types = list(StepType)
                    play_modes = list(PlayMode)
                    slot_dict["seq_enabled"] = mm.get_mode(slot_id - 1) == MotionMode.SEQ
                    slot_dict["seq_rate"] = seq_engine.rate_index
                    slot_dict["seq_length"] = seq.length
                    slot_dict["seq_play_mode"] = play_modes.index(seq.play_mode) if seq.play_mode in play_modes else 0
                    slot_dict["seq_steps"] = [
                        {
                            "step_type": step_types.index(s.step_type) if s.step_type in step_types else 1,
                            "note": s.note,
                            "velocity": s.velocity,
                        }
                        for s in seq.steps
                    ]
            slots.append(SlotState.from_dict(slot_dict))

        channels = []
        for ch_id in range(1, 9):
            ch_widget = self.main.mixer_panel.channels[ch_id]
            channels.append(ChannelState.from_dict(ch_widget.get_state()))

        mixer = MixerState(
            channels=channels,
            master_volume=self.main.master_section.get_volume(),
        )

        bpm = self.main.bpm_display.get_bpm()
        master = MasterState.from_dict(self.main.master_section.get_state())
        mod_sources = ModSourcesState.from_dict(self.main.modulator_grid.get_state())
        mod_routing = self.main.mod_routing.to_dict()
        fx = self.main.fx_window.get_state() if self.main.fx_window else FXState()
        fx_slots = FXSlotsState.from_dict(self.main.fx_grid.get_state()) if hasattr(self.main, 'fx_grid') else FXSlotsState()
        midi_mappings = self.main.cc_mapping_manager.to_dict()
        boids = self.main.boid.get_state_dict() if hasattr(self.main, 'boid') else {}
        telemetry = {}
        if getattr(self.main, 'telemetry_controller', None) is not None:
            telemetry = self.main.telemetry_controller.get_state()
        current_pack = get_current_pack()

        state = PresetState(
            name=name,
            pack=current_pack,
            slots=slots,
            mixer=mixer,
            bpm=bpm,
            master=master,
            mod_sources=mod_sources,
            mod_routing=mod_routing,
            fx=fx,
            fx_slots=fx_slots,
            midi_mappings=midi_mappings,
            boids=boids,
            telemetry=telemetry,
        )
        
        state.version = PRESET_VERSION
        state.created = datetime.now().isoformat()

        try:
            with open(filepath, "w") as f:
                f.write(state.to_json(indent=2))
            self.main.preset_name.setText(name)
            logger.info(f"Preset saved: {filepath}", component="PRESET")
            self.main._clear_dirty(name, filepath)
        except Exception as e:
            logger.error(f"Failed to save preset: {e}", component="PRESET")
            QMessageBox.warning(self.main, "Error", f"Failed to save preset:\n{e}")

    def _load_preset(self):
        """Load preset from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self.main,
            "Load Preset",
            str(self.preset_manager.presets_dir),
            "Preset Files (*.json)",
        )

        if filepath:
            try:
                filepath = Path(filepath)
                state = self.preset_manager.load(filepath)
                self._apply_preset(state)
                self.main.preset_name.setText(state.name)
                logger.info(f"Preset loaded: {state.name}", component="PRESET")
                self.main._clear_dirty(state.name, filepath)
            except Exception as e:
                logger.error(f"Failed to load preset: {e}", component="PRESET")
                QMessageBox.warning(self.main, "Error", f"Failed to load preset:\n{e}")

    def _apply_preset(self, state: PresetState):
        """Apply preset state to all components."""
        if state.pack is not None:
            if not self.main.pack_selector.set_pack(state.pack):
                logger.warning(f"Pack '{state.pack}' not found, using Core", component="PRESET")
        
        for i, slot_state in enumerate(state.slots):
            slot_id = i + 1
            if slot_id <= 8:
                slot_widget = self.main.generator_grid.slots[slot_id]
                slot_widget.set_state(slot_state.to_dict())

        # Restore ARP settings to each slot's engine
        if hasattr(self.main, 'keyboard') and hasattr(self.main.keyboard, 'arp_manager'):
            from src.gui.arp_engine import ArpPattern
            from src.model.sequencer import MotionMode
            patterns = list(ArpPattern)
            mm = getattr(self.main.keyboard, 'motion_manager', None)
            for i, slot_state in enumerate(state.slots):
                if i < 8:
                    engine = self.main.keyboard.arp_manager.get_engine(i)
                    pattern_idx = slot_state.arp_pattern
                    pattern = patterns[pattern_idx] if 0 <= pattern_idx < len(patterns) else ArpPattern.UP
                    engine.set_rate(slot_state.arp_rate)
                    engine.set_pattern(pattern)
                    engine.set_octaves(slot_state.arp_octaves)
                    engine.toggle_hold(slot_state.arp_hold)
                    engine.toggle_arp(slot_state.arp_enabled)
                    # R13: Disarm RST on preset load (transient, not saved)
                    engine.runtime.rst_fabric_idx = None
                    # Set MotionMode.ARP so fabric ticks reach the engine
                    if mm is not None and slot_state.arp_enabled:
                        mm.set_mode(i, MotionMode.ARP)

        # Restore SEQ settings to each slot's engine
        if hasattr(self.main, 'keyboard') and hasattr(self.main.keyboard, 'motion_manager'):
            from src.model.sequencer import StepType, PlayMode, MotionMode, SeqStep
            step_types = list(StepType)
            play_modes = list(PlayMode)
            mm = self.main.keyboard.motion_manager
            for i, slot_state in enumerate(state.slots):
                if i < 8:
                    seq_engine = mm.get_seq_engine(i)
                    if seq_engine is not None:
                        # Restore rate
                        seq_engine._rate_index = max(0, min(slot_state.seq_rate, 6))
                        # Restore length
                        seq_engine.settings.length = max(1, min(slot_state.seq_length, 16))
                        # Restore play mode
                        pm_idx = slot_state.seq_play_mode
                        seq_engine.settings.play_mode = play_modes[pm_idx] if 0 <= pm_idx < len(play_modes) else PlayMode.FORWARD
                        # Restore steps
                        if slot_state.seq_steps:
                            for j, step_dict in enumerate(slot_state.seq_steps[:16]):
                                if isinstance(step_dict, dict):
                                    st_idx = step_dict.get("step_type", 1)
                                    st = step_types[st_idx] if 0 <= st_idx < len(step_types) else StepType.REST
                                    seq_engine.settings.steps[j] = SeqStep(
                                        step_type=st,
                                        note=step_dict.get("note", 60),
                                        velocity=step_dict.get("velocity", 100),
                                    )
                            seq_engine.steps_version += 1
                        # Restore SEQ enabled state (start playback if was active)
                        if slot_state.seq_enabled:
                            mm.set_mode(i, MotionMode.SEQ)

        for i, channel_state in enumerate(state.mixer.channels):
            ch_id = i + 1
            if ch_id in self.main.mixer_panel.channels:
                self.main.mixer_panel.channels[ch_id].set_state(channel_state.to_dict())

        self.main.master_section.set_volume(state.mixer.master_volume)
        
        if state.bpm != 120:
            self.main.bpm_display.set_bpm(state.bpm)
            self.main.on_bpm_changed(state.bpm)
        
        if state.version >= 2 and hasattr(state, 'master'):
            self.main.master_section.set_state(state.master.to_dict())
        
        if state.version >= 2:
            self.main.modulator_grid.set_state(state.mod_sources.to_dict())
            self.main.modulation._sync_mod_sources()

        # Load mod routing with exact replacement semantics (per spec 5.2)
        if state.mod_routing.get("connections") or state.mod_routing.get("ext_mod_routes"):
            self._load_mod_routing_with_osc_projection(state.mod_routing)
            if self.main.mod_matrix_window:
                self.main.mod_matrix_window.sync_from_state()
            # Refresh slider visualizations for loaded routes
            self.main.modulation.refresh_all_mod_visualizations()
        elif not state.mod_routing.get("connections"):
            # Empty preset - clear all routes
            self.main.mod_routing.clear()
            if self.main.mod_matrix_window:
                self.main.mod_matrix_window.sync_from_state()
        
        if self.main.fx_window:
            self.main.fx_window.set_state(state.fx)

        # Load FX slots state (UI Refresh Phase 6)
        if hasattr(self.main, 'fx_grid') and hasattr(state, 'fx_slots'):
            self.main.fx_grid.load_state(state.fx_slots.to_dict())
            if self.main.osc_connected:
                self.main.fx_grid.sync_to_sc()

        # Load boid state if present
        if state.boids and hasattr(self.main, 'boid'):
            self.main.boid.load_state_dict(state.boids)
            # Update panel from state
            if hasattr(self.main, 'boid_panel'):
                s = self.main.boid.state
                self.main.boid_panel.set_enabled(s.enabled)
                self.main.boid_panel.set_count(s.boid_count)
                self.main.boid_panel.set_dispersion(s.dispersion)
                self.main.boid_panel.set_energy(s.energy)
                self.main.boid_panel.set_fade(s.fade)
                self.main.boid_panel.set_depth(s.depth)
                self.main.boid_panel.set_seed(s.seed)
                self.main.boid_panel.set_seed_locked(s.seed_locked)
                self.main.boid_panel.set_zone_gen(s.zone_gen)
                self.main.boid_panel.set_zone_mod(s.zone_mod)
                self.main.boid_panel.set_zone_chan(s.zone_chan)
                self.main.boid_panel.set_zone_fx(s.zone_fx)
                self.main.boid_panel.set_row_slot1(s.row_slot1)
                self.main.boid_panel.set_row_slot2(s.row_slot2)
                self.main.boid_panel.set_row_slot3(s.row_slot3)
                self.main.boid_panel.set_row_slot4(s.row_slot4)
                self.main.boid_panel.set_preset(s.behavior_preset)

        # Load telemetry tuning state (INV, OS, BODY, OFS)
        if state.telemetry and getattr(self.main, 'telemetry_controller', None) is not None:
            self.main.telemetry_controller.set_state(state.telemetry)
            # Sync widget UI if open
            tw = getattr(self.main, '_telemetry_widget', None)
            if tw is not None:
                tw.inv_btn.setChecked(state.telemetry.get('phase_inverted', False))
                offset_slider = int(state.telemetry.get('phase_offset', 0.0) * 1280.0)
                tw.os_slider.setValue(max(-640, min(640, offset_slider)))
                body_slider = int(state.telemetry.get('body_gain', 1.0) * 1000)
                tw.body_slider.setValue(max(250, min(1000, body_slider)))
                ofs_slider = int(state.telemetry.get('v_offset', 0.0) * 1000)
                tw.ofs_slider.setValue(max(-200, min(200, ofs_slider)))

        if state.midi_mappings:
            for controls in self.main.cc_mapping_manager.get_all_mappings().values():
                for control in controls:
                    if hasattr(control, 'set_midi_mapped'):
                        control.set_midi_mapped(False)
            self.main.cc_mapping_manager.from_dict(state.midi_mappings, self.main.midi_cc._find_control_by_name)
            self.main.midi_cc._update_midi_status()
            self.main._show_toast("MIDI mappings loaded from preset")

        # Resend MIDI device to SC after preset load
        if self.main.osc_connected:
            current_midi = self.main.midi_selector.get_current_device()
            if current_midi:
                port_index = self.main.midi_selector.get_port_index(current_midi)
                if port_index >= 0:
                    self.main.osc.client.send_message(OSC_PATHS["midi_device"], [port_index])
                    logger.debug(f"Resent MIDI device: {current_midi} (port {port_index})", component="PRESET")

    def _init_preset(self):
        """Reset to Init.json if it exists, else default empty state (Cmd+N / Ctrl+N)."""
        init_path = self.preset_manager.presets_dir / "Init.json"

        if init_path.exists():
            # Load Init.json as the default state
            try:
                state = self.preset_manager.load(init_path)
                self._apply_preset(state)
                self.main.mod_routing.clear()

                if self.main.mod_matrix_window:
                    self.main.mod_matrix_window.sync_from_state()

                if self.main.fx_window:
                    self.main.fx_window.set_state(state.fx if hasattr(state, 'fx') else FXState())

                if hasattr(self.main, 'fx_grid'):
                    fx_slots = state.fx_slots if hasattr(state, 'fx_slots') else FXSlotsState()
                    self.main.fx_grid.load_state(fx_slots.to_dict())
                    if self.main.osc_connected:
                        self.main.fx_grid.sync_to_sc()

                self.main.pack_selector.set_pack(state.pack_name if hasattr(state, 'pack_name') else "")
                self.main.preset_name.setText("Init")
                self.main._clear_dirty("Init", init_path)
                logger.info(f"Preset loaded: Init (from {init_path})", component="PRESET")
                return
            except Exception as e:
                logger.warning(f"Failed to load Init.json, using defaults: {e}", component="PRESET")

        # Fallback to hardcoded defaults
        state = PresetState()
        self._apply_preset(state)
        self.main.mod_routing.clear()

        if self.main.mod_matrix_window:
            self.main.mod_matrix_window.sync_from_state()

        if self.main.fx_window:
            self.main.fx_window.set_state(FXState())

        if hasattr(self.main, 'fx_grid'):
            self.main.fx_grid.load_state(FXSlotsState().to_dict())
            if self.main.osc_connected:
                self.main.fx_grid.sync_to_sc()

        self.main.pack_selector.set_pack("")
        self.main.preset_name.setText("Init")
        self.main._clear_dirty("Init", None)
        logger.info("Preset initialized to defaults", component="PRESET")

    def _apply_preset_from_path(self, filepath: Path):
        """
        Load and apply preset from a specific path (R1.1 - used by PresetBrowser).

        Args:
            filepath: Path to preset file
        """
        try:
            state = self.preset_manager.load(filepath)
            self._apply_preset(state)
            self.main.preset_name.setText(state.name)
            logger.info(f"Preset loaded: {state.name}", component="PRESET")
            self.main._clear_dirty(state.name, filepath)
        except Exception as e:
            logger.error(f"Failed to load preset: {e}", component="PRESET")
            QMessageBox.warning(self.main, "Error", f"Failed to load preset:\n{e}")

    def _save_preset_to_path(self, filepath: Path, name: str):
        """
        Save current state to a specific path (R1.1 - used by PresetBrowser).

        Args:
            filepath: Destination path
            name: Preset name
        """
        self._do_save_preset(name, filepath)

    def _load_mod_routing_with_osc_projection(self, mod_routing_data: dict):
        """
        Load mod routing with exact replacement semantics and OSC projection.

        Per spec (5.2 Load + 5.5 Backend Projection):
        1. Parse preset into desired route sets
        2. Compute removal sets (key-disjoint from desired)
        3. Replace local state
        4. Project to backend: removes then adds

        Removes are key-specific (Invariant #13), so even if packets arrive
        out-of-order, removes cannot delete desired routes.
        """
        # Get deltas from load operation
        removed_gen, removed_ext, added_gen, added_ext = \
            self.main.mod_routing.load_from_preset(mod_routing_data)

        # Project to backend (best-effort, exceptions logged not fatal)
        if self.main.osc_connected:
            # Send removes first (generator routes use unified bus system)
            for conn in removed_gen:
                try:
                    source_key = _build_source_key(conn.source_bus)
                    target_key = _build_target_key(conn.target_slot, conn.target_param)
                    self.main.osc.client.send_message(
                        OSC_PATHS['bus_route_remove'],
                        [source_key, target_key]
                    )
                except Exception as e:
                    logger.warning(f"Failed to send gen route remove: {e}", component="PRESET")

            for conn in removed_ext:
                try:
                    self.main.osc.client.send_message(
                        OSC_PATHS['extmod_remove_route'],
                        [conn.source_bus, conn.target_str]
                    )
                except Exception as e:
                    logger.warning(f"Failed to send ext route remove: {e}", component="PRESET")

            # Send adds/upserts (generator routes use unified bus system)
            for conn in added_gen:
                try:
                    source_key = _build_source_key(conn.source_bus)
                    target_key = _build_target_key(conn.target_slot, conn.target_param)
                    self.main.osc.client.send_message(
                        OSC_PATHS['bus_route_set'],
                        [source_key, target_key,
                         conn.depth, conn.amount, conn.offset,
                         conn.polarity.value, int(conn.invert)]
                    )
                except Exception as e:
                    logger.warning(f"Failed to send gen route add: {e}", component="PRESET")

            for conn in added_ext:
                try:
                    self.main.osc.client.send_message(
                        OSC_PATHS['extmod_add_route'],
                        [conn.source_bus, conn.target_str,
                         conn.depth, conn.amount, conn.offset,
                         conn.polarity.value, int(conn.invert)]
                    )
                except Exception as e:
                    logger.warning(f"Failed to send ext route add: {e}", component="PRESET")

            logger.debug(
                f"Mod routing loaded: -{len(removed_gen)}/{len(removed_ext)} gen/ext, "
                f"+{len(added_gen)}/{len(added_ext)} gen/ext",
                component="PRESET"
            )
