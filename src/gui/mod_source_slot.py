"""
Mod Source Slot Component
Individual modulation source with 3 outputs

Follows GeneratorSlot patterns but simplified:
- No filter, envelope, or channel strip
- 3 outputs per slot (A/B/C or X/Y/Z)
- Per-output waveform, phase, polarity (LFO)
- Per-output polarity only (Sloth)
- Integrated scope placeholder
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES
from .widgets import CycleButton, DragSlider
from src.config import (
    MOD_GENERATOR_CYCLE,
    MOD_LFO_WAVEFORMS,
    MOD_LFO_PHASES,
    MOD_POLARITY,
    MOD_OUTPUTS_PER_SLOT,
    get_mod_generator_custom_params,
    get_mod_generator_output_config,
    get_mod_output_labels,
    map_value,
)


class ModSourceSlot(QWidget):
    """A single mod source slot with 3 outputs."""
    
    # Signals
    generator_changed = pyqtSignal(int, str)  # slot_id, generator_name
    parameter_changed = pyqtSignal(int, str, float)  # slot_id, param_key, value
    output_wave_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, wave_index
    output_phase_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, phase_index
    output_polarity_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, polarity (0=UNI, 1=BI)
    
    def __init__(self, slot_id, default_generator="Empty", parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.default_generator = default_generator
        self.generator_name = "Empty"
        self.output_config = "fixed"
        
        # UI element refs
        self.gen_button = None
        self.param_sliders = {}
        self.output_rows = []  # List of output row widgets
        
        self.setup_ui()
        self.update_for_generator(default_generator)
        
    def setup_ui(self):
        """Build the slot UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Header row: slot number + generator selector
        header = QHBoxLayout()
        header.setSpacing(6)
        
        # Slot number
        slot_label = QLabel(f"MOD {self.slot_id}")
        slot_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        slot_label.setStyleSheet(f"color: {COLORS['text_bright']};")
        header.addWidget(slot_label)
        
        header.addStretch()
        
        # Generator selector button
        initial_idx = MOD_GENERATOR_CYCLE.index(self.default_generator) if self.default_generator in MOD_GENERATOR_CYCLE else 0
        self.gen_button = CycleButton(MOD_GENERATOR_CYCLE, initial_index=initial_idx)
        self.gen_button.setFixedSize(60, 22)
        self.gen_button.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.gen_button.setStyleSheet(button_style('submenu'))
        self.gen_button.value_changed.connect(self._on_generator_changed)
        header.addWidget(self.gen_button)
        
        layout.addLayout(header)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)
        
        # Parameters section (dynamic based on generator)
        self.params_container = QWidget()
        self.params_layout = QHBoxLayout(self.params_container)
        self.params_layout.setContentsMargins(0, 4, 0, 4)
        self.params_layout.setSpacing(8)
        layout.addWidget(self.params_container)
        
        # Outputs section
        self.outputs_container = QWidget()
        self.outputs_layout = QVBoxLayout(self.outputs_container)
        self.outputs_layout.setContentsMargins(0, 0, 0, 0)
        self.outputs_layout.setSpacing(4)
        layout.addWidget(self.outputs_container)
        
        # Scope display
        from .mod_scope import ModScope
        self.scope = ModScope(history_length=100)
        self.scope.setFixedHeight(50)
        self.scope.setStyleSheet(f"""
            border: 1px solid {COLORS['border']};
            border-radius: 3px;
        """)
        layout.addWidget(self.scope)
        
        layout.addStretch()
        
        # Base styling
        self.setStyleSheet(f"""
            ModSourceSlot {{
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['background_light']};
            }}
        """)
        self.setMinimumWidth(140)
        
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
            self._add_param_slider(param)
        self.params_layout.addStretch()
        
        # Build output rows
        for i in range(MOD_OUTPUTS_PER_SLOT):
            self._add_output_row(i, output_labels[i])
            
        # Update styling
        self._update_style_for_generator(gen_name)
        
    def _setup_empty_state(self):
        """Setup minimal UI for Empty generator."""
        empty_label = QLabel("—")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet(f"color: {COLORS['text']};")
        self.params_layout.addWidget(empty_label)
        
        # Clear and dim the scope
        self.scope.clear()
        self.scope.setEnabled(False)
        self.setStyleSheet(f"""
            ModSourceSlot {{
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['background']};
            }}
        """)
        
    def _add_param_slider(self, param):
        """Add a parameter slider."""
        container = QVBoxLayout()
        container.setSpacing(2)
        
        # Label
        label = QLabel(param.get('label', param['key'].upper()[:4]))
        label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['text']};")
        label.setToolTip(param.get('tooltip', ''))
        container.addWidget(label)
        
        # Slider
        slider = DragSlider()
        slider.setFixedWidth(25)
        slider.setFixedHeight(60)
        default = param.get('default', 0.5)
        slider.setValue(int(default * 1000))
        
        key = param['key']
        slider.valueChanged.connect(
            lambda val, k=key, p=param: self._on_param_changed(k, val, p)
        )
        container.addWidget(slider, alignment=Qt.AlignCenter)
        
        self.param_sliders[key] = slider
        self.params_layout.addLayout(container)
        
    def _on_param_changed(self, key, slider_value, param):
        """Handle parameter slider change."""
        normalized = slider_value / 1000.0
        real_value = map_value(normalized, param)
        self.parameter_changed.emit(self.slot_id, key, real_value)
        
    def _add_output_row(self, output_idx, label):
        """Add an output row with controls."""
        row = QHBoxLayout()
        row.setSpacing(4)
        
        # Output label
        out_label = QLabel(label)
        out_label.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        out_label.setStyleSheet(f"color: {COLORS['text_bright']};")
        out_label.setFixedWidth(20)
        row.addWidget(out_label)
        
        row_widgets = {'label': out_label}
        
        if self.output_config == "waveform_phase":
            # LFO: waveform + phase + polarity
            wave_btn = CycleButton(MOD_LFO_WAVEFORMS, initial_index=0)
            wave_btn.setFixedSize(40, 20)
            wave_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
            wave_btn.setStyleSheet(button_style('submenu'))
            wave_btn.value_changed.connect(
                lambda w, idx=output_idx, wforms=MOD_LFO_WAVEFORMS: self._on_wave_changed(idx, wforms.index(w))
            )
            row.addWidget(wave_btn)
            row_widgets['wave'] = wave_btn
            
            # Default phases: A=0° (idx 0), B=135° (idx 3), C=225° (idx 5)
            # Gives roughly 120° spacing between outputs
            default_phase_indices = [0, 3, 5]
            phase_labels = [f"{p}°" for p in MOD_LFO_PHASES]
            phase_btn = CycleButton(phase_labels, initial_index=default_phase_indices[output_idx])
            phase_btn.setFixedSize(35, 20)
            phase_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
            phase_btn.setStyleSheet(button_style('submenu'))
            phase_btn.value_changed.connect(
                lambda p, idx=output_idx, plabels=phase_labels: self._on_phase_changed(idx, plabels.index(p))
            )
            row.addWidget(phase_btn)
            row_widgets['phase'] = phase_btn
        
        # Polarity button (all generators)
        pol_btn = CycleButton(MOD_POLARITY, initial_index=1)  # Default BI
        pol_btn.setFixedSize(28, 20)
        pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_btn.setStyleSheet(button_style('submenu'))
        pol_btn.value_changed.connect(
            lambda p, idx=output_idx, pols=MOD_POLARITY: self._on_polarity_changed(idx, pols.index(p))
        )
        row.addWidget(pol_btn)
        row_widgets['polarity'] = pol_btn
        
        row.addStretch()
        
        self.outputs_layout.addLayout(row)
        self.output_rows.append(row_widgets)
        
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
            ModSourceSlot {{
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
