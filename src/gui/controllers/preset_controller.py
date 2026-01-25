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
    ChannelState, MasterState, ModSourcesState, FXState
)
from src.utils.logger import logger


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
            slots.append(SlotState.from_dict(slot_widget.get_state()))

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
        midi_mappings = self.main.cc_mapping_manager.to_dict()
        boids = self.main.boid.get_state_dict() if hasattr(self.main, 'boid') else {}
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
            midi_mappings=midi_mappings,
            boids=boids,
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

        # Load boid state if present
        if state.boids and hasattr(self.main, 'boid'):
            self.main.boid.load_state_dict(state.boids)
            # Update panel from state
            if hasattr(self.main, 'boid_panel'):
                s = self.main.boid.state
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
        """Reset to default empty state (Cmd+N / Ctrl+N)."""
        state = PresetState()
        self._apply_preset(state)
        self.main.mod_routing.clear()

        if self.main.mod_matrix_window:
            self.main.mod_matrix_window.sync_from_state()

        if self.main.fx_window:
            self.main.fx_window.set_state(FXState())

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
            # Send removes first
            for conn in removed_gen:
                try:
                    self.main.osc.client.send_message(
                        OSC_PATHS['mod_route_remove'],
                        [conn.source_bus, conn.target_slot, conn.target_param]
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

            # Send adds/upserts
            for conn in added_gen:
                try:
                    self.main.osc.client.send_message(
                        OSC_PATHS['mod_route_add'],
                        [conn.source_bus, conn.target_slot, conn.target_param,
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
