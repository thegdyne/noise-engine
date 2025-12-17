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
)


class ModulatorSlot(QWidget):
    """A single modulator slot with 4 outputs."""
    
    # Signals
    generator_changed = pyqtSignal(int, str)  # slot_id, generator_name
    parameter_changed = pyqtSignal(int, str, float)  # slot_id, param_key, value
    output_wave_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, wave_index
    output_phase_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, phase_index
    output_polarity_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, invert (0=NORM, 1=INV)
    
    def __init__(self, slot_id, default_generator="Empty", parent=None):
        super().__init__(parent)
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
        
        # Build output rows
        for i in range(MOD_OUTPUTS_PER_SLOT):
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
        
    def _on_polarity_changed(self, output_idx, polarity):
        """Handle polarity change."""
        self.output_polarity_changed.emit(self.slot_id, output_idx, polarity)
        
    def _update_style_for_generator(self, gen_name):
        """Update slot styling based on generator type."""
        if gen_name == "LFO":
            border_color = COLORS['accent_mod_lfo']
        elif gen_name == "Sloth":
            border_color = COLORS['accent_mod_sloth']
        else:
            border_color = COLORS['border']
            
        self.setStyleSheet(f"""
            ModulatorSlot {{
                border: 2px solid {border_color};
                border-radius: 6px;
                background-color: {COLORS['background_light']};
            }}
        """)
        # Enable and clear scope for active generator
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
