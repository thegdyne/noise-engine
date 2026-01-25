"""
ModulationController - Handles mod sources, mod routing, and visualization.

Extracted from MainFrame as Phase 6 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

from PyQt5.QtGui import QColor

from src.config import OSC_PATHS, get_param_config, unmap_value
from src.gui.crossmod_osc_bridge import CrossmodOSCBridge
from src.gui.mod_routing_state import Polarity
from src.utils.logger import logger


class ModulationController:
    """Handles mod sources, mod routing, and visualization."""
    
    def __init__(self, main_frame):
        self.main = main_frame

    def _sync_mod_slot_state(self, slot_id, send_generator=True):
        """Push full UI state for one mod slot to SC (SSOT)."""
        if not self.main.osc_connected:
            return
        from src.config import get_mod_generator_custom_params, map_value
        
        slot = self.main.modulator_grid.get_slot(slot_id)
        if not slot:
            return
        
        gen_name = slot.generator_name
        
        if send_generator:
            self.main.osc.client.send_message(OSC_PATHS['mod_generator'], [slot_id, gen_name])
        
        enabled = 1 if gen_name != "Empty" else 0
        self.main.osc.client.send_message(OSC_PATHS['mod_scope_enable'], [slot_id, enabled])
        
        if gen_name == "Empty":
            return
        
        for out_idx, row in enumerate(slot.output_rows):
            if 'wave' in row:
                self.main.osc.client.send_message(OSC_PATHS['mod_output_wave'], [slot_id, out_idx, row['wave'].get_index()])
            if 'phase' in row:
                self.main.osc.client.send_message(OSC_PATHS['mod_output_phase'], [slot_id, out_idx, row['phase'].get_index()])
            if 'polarity' in row:
                self.main.osc.client.send_message(OSC_PATHS['mod_output_polarity'], [slot_id, out_idx, row['polarity'].get_index()])
            if 'tension' in row:
                tension_val = row['tension'].value() / 1000.0
                self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, f"tension{out_idx + 1}", tension_val])
            if 'mass' in row:
                mass_val = row['mass'].value() / 1000.0
                self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, f"mass{out_idx + 1}", mass_val])
        
        for param in get_mod_generator_custom_params(gen_name):
            key = param['key']
            control = slot.param_sliders.get(key)
            if control:
                if hasattr(control, 'get_index'):
                    real_value = float(control.get_index())
                else:
                    normalized = control.value() / 1000.0
                    real_value = map_value(normalized, param)
                self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, key, real_value])
    
    def _sync_mod_sources(self):
        """Send current mod source state to SC on connect."""
        from src.config import MOD_SLOT_COUNT
        
        for slot_id in range(1, MOD_SLOT_COUNT + 1):
            self._sync_mod_slot_state(slot_id, send_generator=True)
            slot = self.main.modulator_grid.get_slot(slot_id)
            if slot:
                logger.debug(f"Synced mod {slot_id}: {slot.generator_name}", component="OSC")
    
    def on_mod_generator_changed(self, slot_id, gen_name):
        """Handle mod source generator change - full sync to SC."""
        if self.main.osc_connected:
            self._sync_mod_slot_state(slot_id, send_generator=True)
        logger.debug(f"Mod {slot_id} generator: {gen_name}", component="OSC")
        self.main._mark_dirty()

    def on_mod_param_changed(self, slot_id, key, value):
        """Handle mod source parameter change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, key, value])
        logger.debug(f"Mod {slot_id} {key}: {value:.3f}", component="OSC")
        
    def on_mod_output_wave(self, slot_id, output_idx, wave_index):
        """Handle mod output waveform change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_output_wave'], [slot_id, output_idx, wave_index])
        logger.debug(f"Mod {slot_id} out {output_idx} wave: {wave_index}", component="OSC")
        
    def on_mod_output_phase(self, slot_id, output_idx, phase_index):
        """Handle mod output phase change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_output_phase'], [slot_id, output_idx, phase_index])
        logger.debug(f"Mod {slot_id} out {output_idx} phase: {phase_index}", component="OSC")

    def on_mod_output_polarity(self, slot_id, output_idx, polarity):
        """Handle mod output polarity change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_output_polarity'], [slot_id, output_idx, polarity])
        logger.debug(f"Mod {slot_id} out {output_idx} polarity: {polarity}", component="OSC")

    def on_mod_env_attack(self, slot_id, env_idx, value):
        """Handle ARSEq+ envelope attack change."""
        param_name = ["atkA", "atkB", "atkC", "atkD"][env_idx]
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, value])
        logger.debug(f"Mod {slot_id} env {env_idx} attack: {value:.3f}", component="OSC")

    def on_mod_env_release(self, slot_id, env_idx, value):
        """Handle ARSEq+ envelope release change."""
        param_name = ["relA", "relB", "relC", "relD"][env_idx]
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, value])
        logger.debug(f"Mod {slot_id} env {env_idx} release: {value:.3f}", component="OSC")

    def on_mod_env_curve(self, slot_id, env_idx, value):
        """Handle ARSEq+ envelope curve change."""
        param_name = ["curveA", "curveB", "curveC", "curveD"][env_idx]
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, value])
        logger.debug(f"Mod {slot_id} env {env_idx} curve: {value:.3f}", component="OSC")

    def on_mod_env_sync_mode(self, slot_id, env_idx, mode):
        """Handle ARSEq+ envelope sync mode change."""
        param_name = ["syncModeA", "syncModeB", "syncModeC", "syncModeD"][env_idx]
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, float(mode)])
        logger.debug(f"Mod {slot_id} env {env_idx} sync_mode: {mode}", component="OSC")

    def on_mod_env_loop_rate(self, slot_id, env_idx, rate_idx):
        """Handle ARSEq+ envelope loop rate change."""
        param_name = ["loopRateA", "loopRateB", "loopRateC", "loopRateD"][env_idx]
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, float(rate_idx)])
        logger.debug(f"Mod {slot_id} env {env_idx} loop_rate: {rate_idx}", component="OSC")

    def on_mod_tension(self, slot_id, output_idx, normalized):
        """Handle SauceOfGrav tension change."""
        param_name = f"tension{output_idx + 1}"
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, normalized])
        logger.debug(f"Mod {slot_id} tension{output_idx + 1}: {normalized:.3f}", component="OSC")

    def on_mod_mass(self, slot_id, output_idx, normalized):
        """Handle SauceOfGrav mass change."""
        param_name = f"mass{output_idx + 1}"
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, normalized])
        logger.debug(f"Mod {slot_id} mass{output_idx + 1}: {normalized:.3f}", component="OSC")

    def on_mod_bus_value(self, bus_idx, value):
        """Handle mod bus value from SC - route to appropriate scope."""
        slot_id = (bus_idx // 4) + 1
        output_idx = bus_idx % 4
        
        slot = self.main.modulator_grid.get_slot(slot_id)
        if slot and hasattr(slot, 'scope') and slot.scope.isEnabled():
            slot.scope.push_value(output_idx, value)
            self.main._mod_scope_dirty.add(slot_id)
    
    def on_mod_values_received(self, values):
        """Handle batched modulated parameter values from SC - update sliders."""
        for slot_id, param, raw_value in values:
            slot = self.main.generator_grid.get_slot(slot_id)
            if slot:
                slider = self._get_slot_slider(slot, param)
                if slider:
                    param_config = get_param_config(param)
                    norm_value = unmap_value(raw_value, param_config)
                    slider.set_modulated_value(norm_value)

    def on_extmod_values_received(self, values):
        """Handle batched extended mod values from SC - update UI widgets."""
        for target_str, norm_value in values:
            parts = target_str.split(":")
            if len(parts) < 3:
                continue

            target_type, identifier, param = parts[0], parts[1], parts[2]

            if target_type == "mod":
                slot_id = int(identifier)
                slot = self.main.modulator_grid.get_slot(slot_id)
                if not slot:
                    continue

                # Map p1-p4 to actual slider key based on generator type
                slider_key = self._map_mod_param_to_slider(slot.generator_name, param)
                if slider_key and slider_key in slot.param_sliders:
                    slider = slot.param_sliders[slider_key]
                    if hasattr(slider, "set_modulated_value"):
                        slider.set_modulated_value(norm_value)

    def _map_mod_param_to_slider(self, gen_name: str, param: str) -> str:
        """
        Map p1-p4 wire params to actual slider keys.

        Must match the ~mapP1P4Param function in mod_slots.scd.
        """
        # P1-P4 mapping per generator type (matches SC)
        mappings = {
            "LFO": {
                "p1": "rate",
                # p2=globalWave, p3=pattern, p4=globalPolarity - no direct sliders
            },
            "ARSEq+": {
                "p1": "rate",
                # p2=globalAtk, p3=globalRel, p4=globalPolarity - no direct sliders
            },
            "SauceOfGrav": {
                "p1": "rate",
                "p3": "calm",
                # p2=globalTension, p4=globalPolarity - no direct sliders
            },
            # Sloth has no p1-p4 support
        }

        gen_mapping = mappings.get(gen_name, {})
        return gen_mapping.get(param)

        
    def _flush_mod_scopes(self):
        """Repaint dirty scopes at throttled rate (~30fps)."""
        for slot_id in list(self.main._mod_scope_dirty):
            slot = self.main.modulator_grid.get_slot(slot_id)
            if slot and hasattr(slot, 'scope') and slot.scope.isEnabled():
                slot.scope.update()
        self.main._mod_scope_dirty.clear()
    
    def _connect_mod_routing_signals(self):
        """Connect mod routing state signals to OSC."""
        self.main.mod_routing.connection_added.connect(self._on_mod_route_added)
        self.main.mod_routing.connection_removed.connect(self._on_mod_route_removed)
        self.main.mod_routing.connection_changed.connect(self._on_mod_route_changed)
        self.main.mod_routing.all_cleared.connect(self._on_mod_routes_cleared)
    
    def _on_mod_route_added(self, conn):
        """Send new mod route to SC and update slider visualization."""
        if self.main.osc_connected:
            if conn.is_extended:
                # Extended route: use /noise/extmod/add_route
                self.main.osc.client.send_message(
                    OSC_PATHS['extmod_add_route'],
                    [conn.source_bus, conn.target_str,
                     conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
                )
                logger.debug(f"Extended mod route added: bus {conn.source_bus} -> {conn.target_str}", component="MOD")
                # Update modulator slider visualization for mod targets
                if conn.target_str.startswith("mod:"):
                    self._update_mod_slider_mod_range(conn.target_str)
            else:
                # Generator route: use /noise/mod/route/add
                self.main.osc.client.send_message(
                    OSC_PATHS['mod_route_add'],
                    [conn.source_bus, conn.target_slot, conn.target_param,
                     conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
                )
                logger.debug(f"Mod route added: bus {conn.source_bus} -> slot {conn.target_slot}.{conn.target_param}", component="MOD")
                # Only update slider visualization for generator routes
                self._update_slider_mod_range(conn.target_slot, conn.target_param)
        
        self.main._mark_dirty()

    def _on_mod_route_removed(self, conn):
        """Send mod route removal to SC and update slider visualization."""
        if self.main.osc_connected:
            if conn.is_extended:
                # Extended route: use /noise/extmod/remove_route
                self.main.osc.client.send_message(
                    OSC_PATHS['extmod_remove_route'],
                    [conn.source_bus, conn.target_str]
                )
                logger.debug(f"Extended mod route removed: bus {conn.source_bus} -> {conn.target_str}", component="MOD")
                # Update modulator slider visualization for mod targets
                if conn.target_str.startswith("mod:"):
                    self._update_mod_slider_mod_range(conn.target_str)
            else:
                # Generator route: use /noise/mod/route/remove
                self.main.osc.client.send_message(
                    OSC_PATHS['mod_route_remove'],
                    [conn.source_bus, conn.target_slot, conn.target_param]
                )
                logger.debug(f"Mod route removed: bus {conn.source_bus} -> slot {conn.target_slot}.{conn.target_param}", component="MOD")
                # Only update slider visualization for generator routes
                self._update_slider_mod_range(conn.target_slot, conn.target_param)
        
        self.main._mark_dirty()

    def _on_mod_route_changed(self, conn):
        """Send mod route parameter change to SC."""
        if self.main.osc_connected:
            if conn.is_extended:
                # Extended route: use /noise/extmod/add_route (upsert)
                self.main.osc.client.send_message(
                    OSC_PATHS['extmod_add_route'],
                    [conn.source_bus, conn.target_str,
                     conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
                )
                # Update modulator slider visualization for mod targets
                if conn.target_str.startswith("mod:"):
                    from PyQt5.QtCore import QTimer
                    target = conn.target_str
                    QTimer.singleShot(0, lambda t=target: self._update_mod_slider_mod_range(t))
            else:
                # Generator route: use /noise/mod/route/set
                self.main.osc.client.send_message(
                    OSC_PATHS['mod_route_set'],
                    [conn.source_bus, conn.target_slot, conn.target_param,
                     conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
                )
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._update_slider_mod_range(conn.target_slot, conn.target_param))
    
    def _get_slot_slider(self, slot, param):
        """Get slider for a param, handling both standard and custom (P1-P5) params."""
        if param.startswith('p') and len(param) == 2 and param[1].isdigit():
            idx = int(param[1]) - 1
            if hasattr(slot, 'custom_sliders') and 0 <= idx < len(slot.custom_sliders):
                return slot.custom_sliders[idx]
            return None
        
        if hasattr(slot, 'sliders') and param in slot.sliders:
            return slot.sliders[param]
        return None
    
    def _update_slider_mod_range(self, slot_id, param):
        """Update slider modulation range visualization based on active connections."""
        from src.config import map_value
        import math
        
        slot = self.main.generator_grid.get_slot(slot_id)
        if not slot:
            return
        
        slider = self._get_slot_slider(slot, param)
        if not slider:
            return
        
        connections = self.main.mod_routing.get_connections_for_target(slot_id, param)
        
        if not connections:
            slider.clear_modulation()
            return
        
        param_config = get_param_config(param)
        min_val = param_config.get('min', 0.0)
        max_val = param_config.get('max', 1.0)
        curve = param_config.get('curve', 'lin')
        oct_range = param_config.get('oct_range', 0)
        
        slider_norm = slider.value() / 1000.0
        base_real = map_value(slider_norm, param_config)
        
        delta_min = 0.0
        delta_max = 0.0
        
        for c in connections:
            r = c.effective_range
            
            if c.polarity == Polarity.BIPOLAR:
                mn, mx = -r, +r
            elif c.polarity == Polarity.UNI_POS:
                mn, mx = 0.0, +r
            else:
                mn, mx = -r, 0.0
            
            mn += c.offset
            mx += c.offset
            
            delta_min += mn
            delta_max += mx
        
        if curve == 'exp' and oct_range > 0:
            if base_real <= 0:
                base_real = min_val if min_val > 0 else 0.001
            mod_max_real = base_real * math.pow(2, delta_max * oct_range)
            mod_min_real = base_real * math.pow(2, delta_min * oct_range)
        else:
            param_range = max_val - min_val
            mod_max_real = base_real + delta_max * param_range
            mod_min_real = base_real + delta_min * param_range
        
        mod_max_real = max(min_val, min(max_val, mod_max_real))
        mod_min_real = max(min_val, min(max_val, mod_min_real))
        
        if mod_min_real > mod_max_real:
            mod_min_real, mod_max_real = mod_max_real, mod_min_real
        
        range_min = unmap_value(mod_min_real, param_config)
        range_max = unmap_value(mod_max_real, param_config)
        
        if len(connections) > 1:
            color = QColor('#00cccc')
        else:
            conn = connections[0]
            mod_slot = conn.source_bus // 4 + 1
            source_slot = self.main.modulator_grid.get_slot(mod_slot)
            if source_slot and source_slot.generator_name == 'Sloth':
                color = QColor('#ff8800')
            else:
                color = QColor('#00ff66')
        
        slider.set_modulation_range(range_min, range_max, range_min, range_max, color)

    def _update_mod_slider_mod_range(self, target_str: str):
        """Update modulator slider modulation range visualization based on active extended connections.

        Args:
            target_str: Extended target like "mod:1:p1"
        """
        parts = target_str.split(":")
        if len(parts) < 3 or parts[0] != "mod":
            return

        slot_id = int(parts[1])
        param = parts[2]  # e.g., "p1"

        slot = self.main.modulator_grid.get_slot(slot_id)
        if not slot:
            return

        # Map p1-p4 to actual slider key
        slider_key = self._map_mod_param_to_slider(slot.generator_name, param)
        if not slider_key or slider_key not in slot.param_sliders:
            return

        slider = slot.param_sliders[slider_key]
        if not hasattr(slider, 'set_modulation_range'):
            return

        # Get all extended connections targeting this target_str
        connections = [c for c in self.main.mod_routing.get_extended_connections()
                      if c.target_str == target_str]

        if not connections:
            slider.clear_modulation()
            return

        # Modulator params are normalized 0-1, linear
        # Calculate combined modulation range
        delta_min = 0.0
        delta_max = 0.0

        for c in connections:
            r = c.effective_range

            if c.polarity == Polarity.BIPOLAR:
                mn, mx = -r, +r
            elif c.polarity == Polarity.UNI_POS:
                mn, mx = 0.0, +r
            else:  # UNI_NEG
                mn, mx = -r, 0.0

            mn += c.offset
            mx += c.offset

            delta_min += mn
            delta_max += mx

        # Get current slider normalized value
        slider_norm = slider.value() / 1000.0

        # Calculate range (clamp to 0-1)
        range_min = max(0.0, min(1.0, slider_norm + delta_min))
        range_max = max(0.0, min(1.0, slider_norm + delta_max))

        if range_min > range_max:
            range_min, range_max = range_max, range_min

        # Color based on source
        if len(connections) > 1:
            color = QColor('#00cccc')  # Cyan for multi-source
        else:
            conn = connections[0]
            mod_slot = conn.source_bus // 4 + 1
            source_slot = self.main.modulator_grid.get_slot(mod_slot)
            if source_slot and source_slot.generator_name == 'Sloth':
                color = QColor('#ff8800')  # Orange for Sloth
            else:
                color = QColor('#00ff66')  # Green default

        slider.set_modulation_range(range_min, range_max, range_min, range_max, color)

    def _on_mod_routes_cleared(self):
        """Handle all routes cleared - send OSC and clear all slider brackets."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['mod_route_clear_all'], [])

        logger.debug("All mod routes cleared", component="MOD")

        # Clear generator slider modulation
        for slot_id in range(1, 9):
            slot = self.main.generator_grid.get_slot(slot_id)
            if slot:
                for param, slider in slot.sliders.items():
                    slider.clear_modulation()
                if hasattr(slot, 'custom_sliders'):
                    for slider in slot.custom_sliders:
                        slider.clear_modulation()

        # Clear modulator slider modulation
        from src.config import MOD_SLOT_COUNT
        for slot_id in range(1, MOD_SLOT_COUNT + 1):
            slot = self.main.modulator_grid.get_slot(slot_id)
            if slot and hasattr(slot, 'param_sliders'):
                for key, widget in slot.param_sliders.items():
                    if hasattr(widget, 'clear_modulation'):
                        widget.clear_modulation()

    def _sync_mod_routing_to_sc(self):
        """Sync all mod routing state to SC (called on reconnect)."""
        if not self.main.osc_connected:
            return
        gen_count = 0
        ext_count = 0
        for conn in self.main.mod_routing.get_all_connections():
            if conn.is_extended:
                # Extended route: use /noise/extmod/add_route
                self.main.osc.client.send_message(
                    OSC_PATHS['extmod_add_route'],
                    [conn.source_bus, conn.target_str,
                     conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
                )
                ext_count += 1
            else:
                # Generator route: use /noise/mod/route/add
                self.main.osc.client.send_message(
                    OSC_PATHS['mod_route_add'],
                    [conn.source_bus, conn.target_slot, conn.target_param,
                     conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
                )

    def refresh_all_mod_visualizations(self):
        """Refresh all modulation slider visualizations based on current routing state.

        Called after preset load to update slider brackets for all active routes.
        """
        # Track which targets we've updated to avoid duplicates
        updated_gen_targets = set()
        updated_ext_targets = set()

        for conn in self.main.mod_routing.get_all_connections():
            if conn.is_extended:
                if conn.target_str not in updated_ext_targets:
                    updated_ext_targets.add(conn.target_str)
                    if conn.target_str.startswith("mod:"):
                        self._update_mod_slider_mod_range(conn.target_str)
                    elif conn.target_str.startswith("send:") or conn.target_str.startswith("chan:"):
                        self._update_chan_slider_mod_range(conn.target_str)
            else:
                target_key = (conn.target_slot, conn.target_param)
                if target_key not in updated_gen_targets:
                    updated_gen_targets.add(target_key)
                    self._update_slider_mod_range(conn.target_slot, conn.target_param)
    
    def _open_mod_matrix(self):
        """Toggle the mod routing matrix window (Cmd+M)."""
        from src.gui.mod_matrix_window import ModMatrixWindow
        
        if self.main.mod_matrix_window is None:
            self.main.mod_matrix_window = ModMatrixWindow(
                self.main.mod_routing, 
                get_target_value_callback=self._get_target_slider_value,
                parent=self.main
            )
            self.main.modulator_grid.generator_changed.connect(self._on_mod_slot_type_changed_for_matrix)
        
        if self.main.mod_matrix_window.isVisible():
            self.main.mod_matrix_window.hide()
            logger.info("Mod matrix window closed", component="MOD")
        else:
            self.main.mod_matrix_window.show()
            # Sync current modulator types to the matrix window
            self._sync_mod_slot_types_to_matrix()
            main_geo = self.main.geometry()
            window_geo = self.main.mod_matrix_window.geometry()
            x = main_geo.x() + (main_geo.width() - window_geo.width()) // 2
            y = main_geo.y() + (main_geo.height() - window_geo.height()) // 2
            self.main.mod_matrix_window.move(x, y)
            self.main.mod_matrix_window.raise_()
            self.main.mod_matrix_window.activateWindow()
            logger.info("Mod matrix window opened", component="MOD")

    def _open_crossmod_matrix(self):
        """Toggle the crossmod routing matrix window (Cmd+X)."""
        from src.gui.crossmod_matrix_window import CrossmodMatrixWindow
        
        if self.main.crossmod_osc is None and self.main.osc_connected:
            self.main.crossmod_osc = CrossmodOSCBridge(self.main.crossmod_state, self.main.osc.client)

        if self.main.crossmod_window is None:
            self.main.crossmod_window = CrossmodMatrixWindow(self.main.crossmod_state, parent=self.main)

        if self.main.crossmod_window.isVisible():
            self.main.crossmod_window.hide()
            logger.info("Crossmod matrix window closed", component="CROSSMOD")
        else:
            self.main.crossmod_window.show()
            main_geo = self.main.geometry()
            window_geo = self.main.crossmod_window.geometry()
            x = main_geo.x() + (main_geo.width() - window_geo.width()) // 2
            y = main_geo.y() + (main_geo.height() - window_geo.height()) // 2
            self.main.crossmod_window.move(x, y)
            self.main.crossmod_window.raise_()
            self.main.crossmod_window.activateWindow()
            logger.info("Crossmod matrix window opened", component="CROSSMOD")

    def _open_fx_window(self):
        """Toggle the FX controls window (Cmd+F)."""
        from src.gui.fx_window import FXWindow
        
        if self.main.fx_window is None:
            self.main.fx_window = FXWindow(self.main.osc if self.main.osc_connected else None, parent=self.main)
        
        if self.main.fx_window.isVisible():
            self.main.fx_window.hide()
            logger.info("FX window closed", component="FX")
        else:
            self.main.fx_window.show()
            self.main.fx_window.raise_()
            self.main.fx_window.activateWindow()
            logger.info("FX window opened", component="FX")

    def _clear_all_mod_routes(self):
        """Clear all modulation routes."""
        self.main.mod_routing.clear()
        logger.info("Cleared all mod routes", component="MOD")

    def _get_target_slider_value(self, slot_id: int, param: str) -> float:
        """Get normalized 0-1 value of a generator parameter slider."""
        slot = self.main.generator_grid.get_slot(slot_id)
        if slot:
            slider = self._get_slot_slider(slot, param)
            if slider:
                return slider.value() / 1000.0
        return 0.5
    
    def _on_mod_slot_type_changed_for_matrix(self, slot_id: int, gen_name: str):
        """Update matrix window and re-apply modulation visualization when mod slot type changes."""
        if self.main.mod_matrix_window:
            self.main.mod_matrix_window.update_mod_slot_type(slot_id, gen_name)

        # Re-apply modulation visualization for any extended routes targeting this slot
        # The sliders are recreated when the type changes, so we need to re-set the ranges
        for param in ["p1", "p2", "p3", "p4"]:
            target_str = f"mod:{slot_id}:{param}"
            # Check if any routes target this
            connections = [c for c in self.main.mod_routing.get_extended_connections()
                          if c.target_str == target_str]
            if connections:
                # Use QTimer to let the new UI settle before updating
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(50, lambda t=target_str: self._update_mod_slider_mod_range(t))

    def _sync_mod_slot_types_to_matrix(self):
        """Sync current modulator types to the matrix window row labels."""
        if not self.main.mod_matrix_window:
            return
        from src.config import MOD_SLOT_COUNT
        for slot_id in range(1, MOD_SLOT_COUNT + 1):
            slot = self.main.modulator_grid.get_slot(slot_id)
            if slot:
                gen_name = slot.generator_name or 'Empty'
                self.main.mod_matrix_window.update_mod_slot_type(slot_id, gen_name)
