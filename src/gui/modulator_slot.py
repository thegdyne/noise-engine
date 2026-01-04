"""
Modulator Slot Component
Individual modulation source with 4 outputs (quadrature)

Follows GeneratorSlot patterns but simplified:
- No filter, envelope, or channel strip
- 4 outputs per slot (A/B/C/D or X/Y/Z/R)
- Per-output waveform, polarity (LFO)
- Per-output polarity only (Sloth)
- Integrated scope display
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal

from .theme import COLORS
from src.config import (
    MOD_LFO_FREQ_MIN,
    MOD_LFO_FREQ_MAX,
    MOD_CLOCK_RATES,
    MOD_OUTPUTS_PER_SLOT,
    get_mod_generator_custom_params,
    get_mod_generator_output_config,
    get_mod_output_labels,
    map_value,
)
from .modulator_slot_builder import (
    build_modulator_slot_ui,
    build_param_slider,
    build_output_row,
    build_arseq_output_row,
    build_saucegrav_output_row,
    build_lfo_rotate_button,
)


class ModulatorSlot(QWidget):
    """A single modulator slot with 4 outputs."""
    
    # Signals
    generator_changed = pyqtSignal(int, str)  # slot_id, generator_name
    parameter_changed = pyqtSignal(int, str, float)  # slot_id, param_key, value
    output_wave_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, wave_index
    output_phase_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, phase_index
    output_polarity_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, invert (0=NORM, 1=INV)

    # ARSEq+ envelope signals
    env_attack_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_release_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_curve_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_sync_mode_changed = pyqtSignal(int, int, int)  # slot_id, env_idx, mode (0=SYNC, 1=LOOP)
    env_loop_rate_changed = pyqtSignal(int, int, int)  # slot_id, env_idx, rate_idx

    # SauceOfGrav output signals
    tension_changed = pyqtSignal(int, int, float)  # slot_id, output_idx, normalized
    mass_changed = pyqtSignal(int, int, float)  # slot_id, output_idx, normalized

    def __init__(self, slot_id, default_generator="Empty", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.slot_id = slot_id
        self.setObjectName(f"mod{slot_id}_slot")  # DEBUG
        self.default_generator = default_generator
        self.generator_name = "Empty"
        self.output_config = "fixed"
        
        # UI element refs (populated by builder)
        self.id_label = None
        self.gen_button = None
        self.params_container = None
        self.params_layout = None
        self.outputs_container = None
        self.outputs_layout = None
        self.scope = None
        self.param_sliders = {}
        self.output_rows = []
        
        # Build UI
        build_modulator_slot_ui(self)
        self.update_for_generator(default_generator)
        
    def _on_generator_changed(self, gen_name):
        """Handle generator selection change."""
        self.update_for_generator(gen_name)
        self.generator_changed.emit(self.slot_id, gen_name)
        
    def update_for_generator(self, gen_name):
        """Rebuild UI for selected generator."""
        self.generator_name = gen_name
        self.output_config = get_mod_generator_output_config(gen_name)
        output_labels = get_mod_output_labels(gen_name)
        custom_params = get_mod_generator_custom_params(gen_name)
        
        # Clear existing params
        self._clear_layout(self.params_layout)
        self.param_sliders = {}
        
        # Clear existing outputs
        self._clear_layout(self.outputs_layout)
        self.output_rows = []
        
        if gen_name == "Empty":
            self._setup_empty_state()
            return
            
        # Build parameter sliders
        for param in custom_params:
            col = build_param_slider(self, param)
            self.params_layout.addWidget(col)

        self.params_layout.addStretch()

        # Add ROT button for LFO (rotates all phases by 45 degrees)
        if gen_name == "LFO":
            rot_col = build_lfo_rotate_button(self)
            self.params_layout.addWidget(rot_col)
        

        # Build output rows (use specialized builder for ARSEq+/SauceOfGrav)
        for i in range(MOD_OUTPUTS_PER_SLOT):
            if gen_name == "ARSEq+":
                row, row_widgets = build_arseq_output_row(self, i, output_labels[i])
            elif gen_name == "SauceOfGrav":
                row, row_widgets = build_saucegrav_output_row(self, i, output_labels[i])
            else:
                row, row_widgets = build_output_row(self, i, output_labels[i], self.output_config)
            self.outputs_layout.addLayout(row)
            self.output_rows.append(row_widgets)
            
        # Update styling
        self._update_style_for_generator(gen_name)
        
    def _setup_empty_state(self):
        """Setup minimal UI for Empty generator."""
        from PyQt5.QtWidgets import QLabel
        empty_label = QLabel("—")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet(f"color: {COLORS['text']};")
        self.params_layout.addWidget(empty_label)
        
        # Clear and dim the scope
        self.scope.clear()
        self.scope.setEnabled(False)
        self.setStyleSheet(f"""
            ModulatorSlot {{
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['background']};
            }}
        """)
    
    def _on_mode_changed(self, key, index):
        """Handle mode button change (0=CLK, 1=FREE)."""
        self.parameter_changed.emit(self.slot_id, key, float(index))
        
    def _on_param_changed(self, key, slider_value, param):
        """Handle parameter slider change."""
        normalized = slider_value / 1000.0
        real_value = map_value(normalized, param)
        
        # Show drag popup with formatted value for rate slider
        slider = self.param_sliders.get(key)
        if slider and hasattr(slider, 'show_drag_value'):
            display_text = self._format_param_value(key, normalized, real_value)
            if display_text:
                slider.show_drag_value(display_text)
        
        self.parameter_changed.emit(self.slot_id, key, real_value)
    
    def _format_param_value(self, key, normalized, real_value):
        """Format parameter value for drag popup display."""
        if key == 'rate':
            # Check current mode (CLK=0, FREE=1)
            mode_btn = self.param_sliders.get('mode')
            if mode_btn and hasattr(mode_btn, 'get_index'):
                mode = mode_btn.get_index()
            else:
                mode = 0  # Default to CLK
            
            if mode == 0:
                # CLK mode: show clock division
                rate_idx = int(normalized * (len(MOD_CLOCK_RATES) - 1))
                rate_idx = max(0, min(rate_idx, len(MOD_CLOCK_RATES) - 1))
                return MOD_CLOCK_RATES[rate_idx]
            else:
                # FREE mode: show Hz (exponential mapping)
                import math
                freq = MOD_LFO_FREQ_MIN * math.pow(MOD_LFO_FREQ_MAX / MOD_LFO_FREQ_MIN, normalized)
                if freq < 1:
                    return f"{freq:.2f}Hz"
                elif freq < 10:
                    return f"{freq:.1f}Hz"
                else:
                    return f"{freq:.0f}Hz"
        
        # Generic params: show as percentage
        pct = int(normalized * 100)
        return f"{pct}%"
        
    def _on_wave_changed(self, output_idx, wave_index):
        """Handle waveform change."""
        self.output_wave_changed.emit(self.slot_id, output_idx, wave_index)
        
    def _on_phase_changed(self, output_idx, phase_index):
        """Handle phase change."""
        self.output_phase_changed.emit(self.slot_id, output_idx, phase_index)

    def _on_rotate_phases(self):
        """Rotate all phase offsets by 45 degrees (one step)."""
        from src.config import MOD_LFO_PHASES
        num_phases = len(MOD_LFO_PHASES)  # 8 phases: 0, 45, 90, ... 315
        
        for i, row_widgets in enumerate(self.output_rows):
            if 'phase' in row_widgets:
                phase_btn = row_widgets['phase']
                current_idx = phase_btn.index
                new_idx = (current_idx + 1) % num_phases
                phase_btn.blockSignals(True)
                phase_btn.set_index(new_idx)
                phase_btn.blockSignals(False)
                # Emit the change to update SC
                self.output_phase_changed.emit(self.slot_id, i, new_idx)

    def _on_polarity_changed(self, output_idx, polarity):
        """Handle polarity change."""
        self.output_polarity_changed.emit(self.slot_id, output_idx, polarity)

    def _on_tension_changed(self, output_idx, value):
        """Handle tension slider change."""
        normalized = value / 1000.0
        self.tension_changed.emit(self.slot_id, output_idx, normalized)

    def _on_mass_changed(self, output_idx, value):
        """Handle mass slider change."""
        normalized = value / 1000.0
        self.mass_changed.emit(self.slot_id, output_idx, normalized)

    def _on_env_attack_changed(self, env_idx, value):
        """Handle ARSEq+ envelope attack change."""
        normalized = value / 1000.0
        self.env_attack_changed.emit(self.slot_id, env_idx, normalized)

    def _on_env_release_changed(self, env_idx, value):
        """Handle ARSEq+ envelope release change."""
        normalized = value / 1000.0
        self.env_release_changed.emit(self.slot_id, env_idx, normalized)

    def _on_env_curve_changed(self, env_idx, value):
        """Handle ARSEq+ envelope curve change."""
        normalized = value / 1000.0
        self.env_curve_changed.emit(self.slot_id, env_idx, normalized)

    def _on_env_sync_mode_changed(self, env_idx, mode):
        """Handle ARSEq+ envelope sync mode change (0=SYNC, 1=LOOP)."""
        self.env_sync_mode_changed.emit(self.slot_id, env_idx, mode)

    def _on_env_loop_rate_changed(self, env_idx, rate_idx):
        """Handle ARSEq+ envelope loop rate change."""
        self.env_loop_rate_changed.emit(self.slot_id, env_idx, rate_idx)

    def _update_style_for_generator(self, gen_name):
        """Apply styling based on generator type."""
        accent_key = {
            "LFO": "accent_mod_lfo",
            "Sloth": "accent_mod_sloth",
            "ARSEq+": "accent_mod_arseq_plus",
            "SauceOfGrav": "accent_mod_sauce_of_grav",
        }.get(gen_name, "accent_mod_lfo")
        accent = COLORS.get(accent_key, COLORS['accent_mod_lfo'])
        
        self.setStyleSheet(f"""
            ModulatorSlot {{
                border: 2px solid {accent};
                border-radius: 6px;
                background-color: {COLORS['background_light']};
            }}
        """)
        self.scope.setEnabled(True)
        self.scope.clear()
        
    def _clear_layout(self, layout):
        """Remove all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def get_state(self) -> dict:
        """Get modulator slot state for preset save (Phase 3)."""
        # Get param values from sliders
        params = {}
        for key, widget in self.param_sliders.items():
            if hasattr(widget, 'value'):
                # Slider: normalize 0-1000 to 0-1
                params[key] = widget.value() / 1000.0
            elif hasattr(widget, 'current_index'):
                # CycleButton: store index as normalized
                params[key] = widget.index

        # Get output states
        output_wave = []
        output_phase = []
        output_polarity = []
        output_tension = []
        output_mass = []
        
        # ARSEq+ envelope states
        env_attack = []
        env_release = []
        env_curve = []
        env_sync_mode = []
        env_loop_rate = []

        for row_widgets in self.output_rows:
            # Wave (if present)
            if 'wave' in row_widgets:
                output_wave.append(row_widgets['wave'].index)
            else:
                output_wave.append(0)

            # Phase (if present)
            if 'phase' in row_widgets:
                output_phase.append(row_widgets['phase'].index)
            else:
                output_phase.append(0)

            # Polarity (always present)
            if 'polarity' in row_widgets:
                output_polarity.append(row_widgets['polarity'].index)
            else:
                output_polarity.append(0)

            # Tension (SauceOfGrav)
            if 'tension' in row_widgets:
                output_tension.append(row_widgets['tension'].value() / 1000.0)
            else:
                output_tension.append(0.5)

            # Mass (SauceOfGrav)
            if 'mass' in row_widgets:
                output_mass.append(row_widgets['mass'].value() / 1000.0)
            else:
                output_mass.append(0.5)

            # ARSEq+ envelope params
            if 'atk' in row_widgets:
                env_attack.append(row_widgets['atk'].value() / 1000.0)
            else:
                env_attack.append(0.5)
                
            if 'rel' in row_widgets:
                env_release.append(row_widgets['rel'].value() / 1000.0)
            else:
                env_release.append(0.5)
                
            if 'curve' in row_widgets:
                env_curve.append(row_widgets['curve'].value() / 1000.0)
            else:
                env_curve.append(0.5)
                
            if 'sync_mode' in row_widgets:
                env_sync_mode.append(row_widgets['sync_mode'].index)
            else:
                env_sync_mode.append(0)
                
            if 'loop_rate' in row_widgets:
                env_loop_rate.append(row_widgets['loop_rate'].index)
            else:
                env_loop_rate.append(6)

        # Pad to 4 outputs if fewer
        while len(output_wave) < 4:
            output_wave.append(0)
        while len(output_phase) < 4:
            output_phase.append(0)
        while len(output_polarity) < 4:
            output_polarity.append(0)
        while len(output_tension) < 4:
            output_tension.append(0.5)
        while len(output_mass) < 4:
            output_mass.append(0.5)
        while len(env_attack) < 4:
            env_attack.append(0.5)
        while len(env_release) < 4:
            env_release.append(0.5)
        while len(env_curve) < 4:
            env_curve.append(0.5)
        while len(env_sync_mode) < 4:
            env_sync_mode.append(0)
        while len(env_loop_rate) < 4:
            env_loop_rate.append(6)

        return {
            "generator_name": self.generator_name,
            "params": params,
            "output_wave": output_wave[:4],
            "output_phase": output_phase[:4],
            "output_polarity": output_polarity[:4],
            "output_tension": output_tension[:4],
            "output_mass": output_mass[:4],
            "env_attack": env_attack[:4],
            "env_release": env_release[:4],
            "env_curve": env_curve[:4],
            "env_sync_mode": env_sync_mode[:4],
            "env_loop_rate": env_loop_rate[:4],
        }

    def set_state(self, state: dict):
        """Apply modulator slot state from preset load (Phase 3)."""
        # Set generator (this rebuilds params and outputs)
        gen_name = state.get("generator_name", "Empty")
        if gen_name != self.generator_name:
            self.update_for_generator(gen_name)
            # Update the button to show the new generator
            if self.gen_button:
                from src.config import MOD_GENERATOR_CYCLE
                if gen_name in MOD_GENERATOR_CYCLE:
                    idx = MOD_GENERATOR_CYCLE.index(gen_name)
                    self.gen_button.blockSignals(True)
                    self.gen_button.set_index(idx)
                    self.gen_button.blockSignals(False)

        # Restore param values
        params = state.get("params", {})
        for key, widget in self.param_sliders.items():
            if key in params:
                val = params[key]
                if hasattr(widget, 'setValue'):
                    # Slider: convert 0-1 to 0-1000
                    widget.blockSignals(True)
                    widget.setValue(int(val * 1000) if isinstance(val, float) else val)
                    widget.blockSignals(False)
                elif hasattr(widget, 'set_index'):
                    # CycleButton: set index
                    widget.blockSignals(True)
                    widget.set_index(int(val) if isinstance(val, (int, float)) else 0)
                    widget.blockSignals(False)

        # Restore output states
        output_wave = state.get("output_wave", [0, 0, 0, 0])
        output_phase = state.get("output_phase", [0, 3, 5, 6])
        output_polarity = state.get("output_polarity", [0, 0, 0, 0])
        output_tension = state.get("output_tension", [0.5, 0.5, 0.5, 0.5])
        output_mass = state.get("output_mass", [0.5, 0.5, 0.5, 0.5])
        
        # ARSEq+ envelope states
        env_attack = state.get("env_attack", [0.5, 0.5, 0.5, 0.5])
        env_release = state.get("env_release", [0.5, 0.5, 0.5, 0.5])
        env_curve = state.get("env_curve", [0.5, 0.5, 0.5, 0.5])
        env_sync_mode = state.get("env_sync_mode", [0, 0, 0, 0])
        env_loop_rate = state.get("env_loop_rate", [6, 6, 6, 6])

        for i, row_widgets in enumerate(self.output_rows):
            if i >= 4:
                break

            # Wave
            if 'wave' in row_widgets and i < len(output_wave):
                row_widgets['wave'].blockSignals(True)
                row_widgets['wave'].set_index(output_wave[i])
                row_widgets['wave'].blockSignals(False)

            # Phase
            if 'phase' in row_widgets and i < len(output_phase):
                row_widgets['phase'].blockSignals(True)
                row_widgets['phase'].set_index(output_phase[i])
                row_widgets['phase'].blockSignals(False)

            # Polarity
            if 'polarity' in row_widgets and i < len(output_polarity):
                row_widgets['polarity'].blockSignals(True)
                row_widgets['polarity'].set_index(output_polarity[i])
                row_widgets['polarity'].blockSignals(False)

            # Tension (SauceOfGrav) - skip if old default (let builder defaults stand)
            if 'tension' in row_widgets and i < len(output_tension):
                if output_tension != [0.5, 0.5, 0.5, 0.5]:  # Only restore if customized
                    row_widgets['tension'].blockSignals(True)
                    row_widgets['tension'].setValue(int(output_tension[i] * 1000))
                    row_widgets['tension'].blockSignals(False)

            # Mass (SauceOfGrav) - skip if old default (let builder defaults stand)
            if 'mass' in row_widgets and i < len(output_mass):
                if output_mass != [0.5, 0.5, 0.5, 0.5]:  # Only restore if customized
                    row_widgets['mass'].blockSignals(True)
                    row_widgets['mass'].setValue(int(output_mass[i] * 1000))
                    row_widgets['mass'].blockSignals(False)

            # ARSEq+ envelope attack
            if 'atk' in row_widgets and i < len(env_attack):
                row_widgets['atk'].blockSignals(True)
                row_widgets['atk'].setValue(int(env_attack[i] * 1000))
                row_widgets['atk'].blockSignals(False)

            # ARSEq+ envelope release
            if 'rel' in row_widgets and i < len(env_release):
                row_widgets['rel'].blockSignals(True)
                row_widgets['rel'].setValue(int(env_release[i] * 1000))
                row_widgets['rel'].blockSignals(False)

            # ARSEq+ envelope curve
            if 'curve' in row_widgets and i < len(env_curve):
                row_widgets['curve'].blockSignals(True)
                row_widgets['curve'].setValue(int(env_curve[i] * 1000))
                row_widgets['curve'].blockSignals(False)

            # ARSEq+ envelope sync mode
            if 'sync_mode' in row_widgets and i < len(env_sync_mode):
                row_widgets['sync_mode'].blockSignals(True)
                row_widgets['sync_mode'].set_index(env_sync_mode[i])
                row_widgets['sync_mode'].blockSignals(False)

            # ARSEq+ envelope loop rate
            if 'loop_rate' in row_widgets and i < len(env_loop_rate):
                row_widgets['loop_rate'].blockSignals(True)
                row_widgets['loop_rate'].set_index(env_loop_rate[i])
                row_widgets['loop_rate'].blockSignals(False)

        # Send all state to SC
        self._send_all_state_to_osc()

    def _send_all_state_to_osc(self):
        """Send all current state to SC after preset load."""
        # Emit generator change
        self.generator_changed.emit(self.slot_id, self.generator_name)

        # Emit all param values
        for key, widget in self.param_sliders.items():
            if hasattr(widget, 'value'):
                normalized = widget.value() / 1000.0
                from src.config import get_mod_generator_custom_params, map_value
                # Find param config to get real value
                for param in get_mod_generator_custom_params(self.generator_name):
                    if param.get('key') == key:
                        real_value = map_value(normalized, param)
                        self.parameter_changed.emit(self.slot_id, key, real_value)
                        break
            elif hasattr(widget, 'index'):
                self.parameter_changed.emit(self.slot_id, key, float(widget.index))

        # Emit output states
        for i, row_widgets in enumerate(self.output_rows):
            if 'wave' in row_widgets:
                self.output_wave_changed.emit(self.slot_id, i, row_widgets['wave'].index)
            if 'phase' in row_widgets:
                self.output_phase_changed.emit(self.slot_id, i, row_widgets['phase'].index)
            if 'polarity' in row_widgets:
                self.output_polarity_changed.emit(self.slot_id, i, row_widgets['polarity'].index)
            if 'tension' in row_widgets:
                self.tension_changed.emit(self.slot_id, i, row_widgets['tension'].value() / 1000.0)
            if 'mass' in row_widgets:
                self.mass_changed.emit(self.slot_id, i, row_widgets['mass'].value() / 1000.0)
            # ARSEq+ envelope signals
            if 'atk' in row_widgets:
                self.env_attack_changed.emit(self.slot_id, i, row_widgets['atk'].value() / 1000.0)
            if 'rel' in row_widgets:
                self.env_release_changed.emit(self.slot_id, i, row_widgets['rel'].value() / 1000.0)
            if 'curve' in row_widgets:
                self.env_curve_changed.emit(self.slot_id, i, row_widgets['curve'].value() / 1000.0)
            if 'sync_mode' in row_widgets:
                self.env_sync_mode_changed.emit(self.slot_id, i, row_widgets['sync_mode'].index)
            if 'loop_rate' in row_widgets:
                self.env_loop_rate_changed.emit(self.slot_id, i, row_widgets['loop_rate'].index)
