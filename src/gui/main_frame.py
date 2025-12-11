"""
Main Frame - Combines all components
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.gui.generator_grid import GeneratorGrid
from src.gui.mixer_panel import MixerPanel
from src.gui.effects_chain import EffectsChain
from src.gui.modulation_sources import ModulationSources
from src.gui.bpm_display import BPMDisplay
from src.gui.theme import COLORS, button_style, FONT_FAMILY, FONT_SIZES
from src.audio.osc_bridge import OSCBridge
from src.config import (
    CLOCK_RATE_INDEX, FILTER_TYPE_INDEX, GENERATORS, GENERATOR_CYCLE,
    BPM_DEFAULT, OSC_PATHS
)


class MainFrame(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Noise Engine")
        self.setMinimumSize(1200, 700)
        self.setGeometry(100, 50, 1400, 800)
        
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        
        self.osc = OSCBridge()
        self.osc_connected = False
        
        self.active_generators = {}
        self.active_effects = {}
        
        self.master_bpm = BPM_DEFAULT
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the main interface layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Left - MOD SOURCES
        self.modulation_sources = ModulationSources()
        self.modulation_sources.setFixedWidth(220)
        content_layout.addWidget(self.modulation_sources)
        
        # Center - GENERATORS
        self.generator_grid = GeneratorGrid(rows=2, cols=4)
        self.generator_grid.generator_selected.connect(self.on_generator_selected)  # Legacy
        self.generator_grid.generator_changed.connect(self.on_generator_changed)
        self.generator_grid.generator_parameter_changed.connect(self.on_generator_param_changed)
        self.generator_grid.generator_custom_parameter_changed.connect(self.on_generator_custom_param_changed)
        self.generator_grid.generator_filter_changed.connect(self.on_generator_filter_changed)
        self.generator_grid.generator_clock_enabled_changed.connect(self.on_generator_clock_enabled)
        self.generator_grid.generator_clock_rate_changed.connect(self.on_generator_clock_rate)
        self.generator_grid.generator_mute_changed.connect(self.on_generator_mute)
        self.generator_grid.generator_midi_channel_changed.connect(self.on_generator_midi_channel)
        content_layout.addWidget(self.generator_grid, stretch=5)
        
        # Right - MIXER
        self.mixer_panel = MixerPanel(num_generators=8)
        self.mixer_panel.generator_volume_changed.connect(self.on_generator_volume_changed)
        self.mixer_panel.generator_muted.connect(self.on_generator_muted)
        self.mixer_panel.generator_solo.connect(self.on_generator_solo)
        self.mixer_panel.master_volume_changed.connect(self.on_master_volume_changed)
        content_layout.addWidget(self.mixer_panel, stretch=1)
        
        main_layout.addLayout(content_layout, stretch=1)
        
        # Bottom - EFFECTS only
        bottom_section = self.create_bottom_section()
        main_layout.addWidget(bottom_section)
        
    def create_top_bar(self):
        """Create top bar."""
        bar = QFrame()
        bar.setFrameShape(QFrame.StyledPanel)
        bar.setStyleSheet(f"background-color: {COLORS['background_highlight']}; border-bottom: 1px solid {COLORS['border_light']};")
        bar.setFixedHeight(60)
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        
        title = QLabel("NOISE ENGINE")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['title'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(title)
        
        layout.addStretch()
        
        self.bpm_display = BPMDisplay(initial_bpm=BPM_DEFAULT)
        self.bpm_display.bpm_changed.connect(self.on_bpm_changed)
        layout.addWidget(self.bpm_display)
        
        layout.addStretch()
        
        preset_label = QLabel("Preset:")
        preset_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(preset_label)
        
        self.preset_name = QLabel("Init")
        self.preset_name.setFont(QFont(FONT_FAMILY, FONT_SIZES['section']))
        self.preset_name.setStyleSheet(f"color: {COLORS['selected_text']};")
        layout.addWidget(self.preset_name)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(button_style('disabled'))
        save_btn.setEnabled(False)
        layout.addWidget(save_btn)
        
        load_btn = QPushButton("Load")
        load_btn.setStyleSheet(button_style('disabled'))
        load_btn.setEnabled(False)
        layout.addWidget(load_btn)
        
        layout.addStretch()
        
        self.connect_btn = QPushButton("Connect SuperCollider")
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['border_light']};
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['text']};
            }}
        """)
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet(f"color: {COLORS['warning_text']};")
        layout.addWidget(self.status_label)
        
        return bar
        
    def create_bottom_section(self):
        """Create bottom section - effects only."""
        container = QFrame()
        container.setFrameShape(QFrame.StyledPanel)
        container.setStyleSheet(f"background-color: {COLORS['background_highlight']}; border-top: 1px solid {COLORS['border_light']};")
        container.setFixedHeight(100)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        self.effects_chain = EffectsChain()
        self.effects_chain.effect_selected.connect(self.on_effect_selected)
        self.effects_chain.effect_amount_changed.connect(self.on_effect_amount_changed)
        layout.addWidget(self.effects_chain)
        
        return container
        
    def on_bpm_changed(self, bpm):
        """Handle BPM change."""
        self.master_bpm = bpm
        self.modulation_sources.set_master_bpm(bpm)
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['clock_bpm'], [bpm])
        
    def toggle_connection(self):
        """Connect/disconnect to SuperCollider."""
        if not self.osc_connected:
            if self.osc.connect():
                self.osc_connected = True
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("● Connected")
                self.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
                self.mixer_panel.set_io_status(audio=True)
                
                self.osc.client.send_message(OSC_PATHS['clock_bpm'], [self.master_bpm])
                self.modulation_sources.set_master_bpm(self.master_bpm)
            else:
                self.status_label.setText("● Connection Failed")
                self.status_label.setStyleSheet(f"color: {COLORS['warning_text']};")
        else:
            self.osc_connected = False
            self.connect_btn.setText("Connect SuperCollider")
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet(f"color: {COLORS['submenu_text']};")
            self.mixer_panel.set_io_status(audio=False)
        
    def on_generator_param_changed(self, slot_id, param_name, value):
        """Handle per-generator parameter change."""
        if self.osc_connected:
            path = OSC_PATHS.get(f'gen_{param_name}', f'/noise/gen/{param_name}')
            self.osc.client.send_message(path, [slot_id, value])
    
    def on_generator_custom_param_changed(self, slot_id, param_index, value):
        """Handle per-generator custom parameter change."""
        if self.osc_connected:
            # Safety clamp to prevent OSC float overflow
            value = max(-1e30, min(1e30, float(value)))
            path = f"{OSC_PATHS['gen_custom']}/{slot_id}/{param_index}"
            self.osc.client.send_message(path, [value])
        
    def on_generator_filter_changed(self, slot_id, filter_type):
        """Handle generator filter type change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_filter_type'], [slot_id, FILTER_TYPE_INDEX[filter_type]])
        
    def on_generator_clock_enabled(self, slot_id, enabled):
        """Handle generator envelope ON/OFF."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_env_enabled'], [slot_id, 1 if enabled else 0])
        
    def on_generator_clock_rate(self, slot_id, rate):
        """Handle generator clock rate change - send index."""
        rate_index = CLOCK_RATE_INDEX.get(rate, 3)  # Default to CLK
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_clock_rate'], [slot_id, rate_index])
        print(f"Gen {slot_id} rate: {rate} (index {rate_index})")
    
    def on_generator_mute(self, slot_id, muted):
        """Handle generator mute from slot button."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_mute'], [slot_id, 1 if muted else 0])
        print(f"Gen {slot_id} mute: {muted}")
    
    def on_generator_midi_channel(self, slot_id, channel):
        """Handle generator MIDI channel change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_midi_channel'], [slot_id, channel])
        print(f"Gen {slot_id} MIDI channel: {channel}")
        
    def on_generator_selected(self, slot_id):
        """Handle generator slot selection (legacy click handler)."""
        # Legacy - cycles through generators on click
        # New behavior uses on_generator_changed from CycleButton
        pass
    
    def on_generator_changed(self, slot_id, new_type):
        """Handle generator type change from CycleButton."""
        synth_name = GENERATORS.get(new_type)
        
        # Update the slot (custom params, etc)
        self.generator_grid.set_generator_type(slot_id, new_type)
        
        if synth_name:
            if self.osc_connected:
                self.osc.client.send_message(OSC_PATHS['start_generator'], [slot_id, synth_name])
            
            self.generator_grid.set_generator_active(slot_id, True)
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(True)
            self.active_generators[slot_id] = synth_name
        else:
            if self.osc_connected:
                self.osc.client.send_message(OSC_PATHS['stop_generator'], [slot_id])
            
            self.generator_grid.set_generator_active(slot_id, False)
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(False)
            if slot_id in self.active_generators:
                del self.active_generators[slot_id]
                
    def on_effect_selected(self, slot_id):
        """Handle effect slot selection."""
        current_type = self.effects_chain.get_slot(slot_id).effect_type
        
        if current_type == "Empty":
            new_type = "Fidelity"
            slot = self.effects_chain.get_slot(slot_id)
            slot.set_amount(0.75)
            self.active_effects[slot_id] = new_type
            if self.osc_connected:
                self.osc.client.send_message(OSC_PATHS['fidelity_amount'], [0.75])
        elif current_type == "Fidelity":
            new_type = "Empty"
            if slot_id in self.active_effects:
                del self.active_effects[slot_id]
            if self.osc_connected:
                self.osc.client.send_message(OSC_PATHS['fidelity_amount'], [1.0])
        else:
            new_type = "Empty"
        
        self.effects_chain.set_effect_type(slot_id, new_type)
            
    def on_effect_amount_changed(self, slot_id, amount):
        """Handle effect amount change."""
        if self.osc_connected and slot_id in self.active_effects:
            self.osc.client.send_message(OSC_PATHS['fidelity_amount'], [amount])
        
    def on_generator_volume_changed(self, gen_id, volume):
        """Handle generator volume change."""
        pass
        
    def on_generator_muted(self, gen_id, muted):
        """Handle generator mute."""
        pass
        
    def on_generator_solo(self, gen_id, solo):
        """Handle generator solo."""
        pass
        
    def on_master_volume_changed(self, volume):
        """Handle master volume change."""
        pass
