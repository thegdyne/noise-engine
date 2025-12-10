"""
Main Frame - Combines all components
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QSlider)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.gui.modulation_panel import ModulationPanel
from src.gui.generator_grid import GeneratorGrid
from src.gui.mixer_panel import MixerPanel
from src.gui.effects_chain import EffectsChain
from src.gui.modulation_sources import ModulationSources
from src.audio.osc_bridge import OSCBridge


class MainFrame(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Noise Engine")
        self.setMinimumSize(1400, 850)
        self.setGeometry(100, 50, 1600, 900)
        
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        
        self.osc = OSCBridge()
        self.osc_connected = False
        
        self.active_generators = {}
        self.active_effects = {}
        
        self.master_bpm = 120
        
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
        
        self.modulation_panel = ModulationPanel()
        self.modulation_panel.parameter_changed.connect(self.on_parameter_changed)
        content_layout.addWidget(self.modulation_panel, stretch=2)
        
        self.generator_grid = GeneratorGrid(rows=2, cols=4)
        self.generator_grid.generator_selected.connect(self.on_generator_selected)
        self.generator_grid.generator_parameter_changed.connect(self.on_generator_param_changed)
        self.generator_grid.generator_filter_changed.connect(self.on_generator_filter_changed)
        self.generator_grid.generator_clock_changed.connect(self.on_generator_clock_changed)
        content_layout.addWidget(self.generator_grid, stretch=5)
        
        self.mixer_panel = MixerPanel(num_generators=8)
        self.mixer_panel.generator_volume_changed.connect(self.on_generator_volume_changed)
        self.mixer_panel.generator_muted.connect(self.on_generator_muted)
        self.mixer_panel.generator_solo.connect(self.on_generator_solo)
        self.mixer_panel.master_volume_changed.connect(self.on_master_volume_changed)
        content_layout.addWidget(self.mixer_panel, stretch=1)
        
        main_layout.addLayout(content_layout, stretch=1)
        
        bottom_section = self.create_bottom_section()
        main_layout.addWidget(bottom_section)
        
    def create_top_bar(self):
        """Create top bar."""
        bar = QFrame()
        bar.setFrameShape(QFrame.StyledPanel)
        bar.setStyleSheet("background-color: #2a2a2a; border-bottom: 1px solid #555;")
        bar.setFixedHeight(50)
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        
        title = QLabel("NOISE ENGINE")
        title_font = QFont('Helvetica', 16, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addStretch()
        
        clock_label = QLabel("Clock:")
        layout.addWidget(clock_label)
        
        self.bpm_label = QLabel("120 BPM")
        bpm_font = QFont('Courier', 12, QFont.Bold)
        self.bpm_label.setFont(bpm_font)
        self.bpm_label.setStyleSheet("color: #44ff44;")
        layout.addWidget(self.bpm_label)
        
        self.bpm_slider = QSlider(Qt.Horizontal)
        self.bpm_slider.setMinimum(20)
        self.bpm_slider.setMaximum(300)
        self.bpm_slider.setValue(120)
        self.bpm_slider.setFixedWidth(150)
        self.bpm_slider.valueChanged.connect(self.on_bpm_changed)
        layout.addWidget(self.bpm_slider)
        
        layout.addStretch()
        
        preset_label = QLabel("Preset:")
        layout.addWidget(preset_label)
        
        self.preset_name = QLabel("Init")
        preset_font = QFont('Helvetica', 12)
        self.preset_name.setFont(preset_font)
        self.preset_name.setStyleSheet("color: #0066cc;")
        layout.addWidget(self.preset_name)
        
        save_btn = QPushButton("Save")
        save_btn.setEnabled(False)
        layout.addWidget(save_btn)
        
        load_btn = QPushButton("Load")
        load_btn.setEnabled(False)
        layout.addWidget(load_btn)
        
        layout.addStretch()
        
        self.connect_btn = QPushButton("Connect SuperCollider")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        
        return bar
        
    def create_bottom_section(self):
        """Create bottom section."""
        container = QFrame()
        container.setFrameShape(QFrame.StyledPanel)
        container.setStyleSheet("background-color: #2a2a2a; border-top: 1px solid #555;")
        container.setFixedHeight(120)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        self.modulation_sources = ModulationSources()
        layout.addWidget(self.modulation_sources, stretch=2)
        
        middle = QFrame()
        middle.setStyleSheet("border: 1px solid #333; border-radius: 3px;")
        middle_layout = QVBoxLayout(middle)
        middle_label = QLabel("[TBD]")
        middle_label.setAlignment(Qt.AlignCenter)
        middle_label.setStyleSheet("color: #444; border: none;")
        middle_layout.addWidget(middle_label)
        layout.addWidget(middle, stretch=1)
        
        self.effects_chain = EffectsChain()
        self.effects_chain.effect_selected.connect(self.on_effect_selected)
        self.effects_chain.effect_amount_changed.connect(self.on_effect_amount_changed)
        layout.addWidget(self.effects_chain, stretch=2)
        
        return container
        
    def on_bpm_changed(self, bpm):
        """Handle BPM change."""
        self.master_bpm = bpm
        self.bpm_label.setText(f"{bpm} BPM")
        self.modulation_sources.set_master_bpm(bpm)
        print(f"Master clock: {bpm} BPM")
        
    def toggle_connection(self):
        """Connect/disconnect to SuperCollider."""
        if not self.osc_connected:
            if self.osc.connect():
                self.osc_connected = True
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("● Connected")
                self.status_label.setStyleSheet("color: green;")
                self.mixer_panel.set_io_status(audio=True)
                
                for param_id in self.modulation_panel.parameters.keys():
                    value = self.modulation_panel.get_parameter_value(param_id)
                    if value is not None:
                        self.osc.send_parameter(param_id, value)
                
                self.modulation_sources.set_master_bpm(self.master_bpm)
                
                print("✓ Connected to SuperCollider")
                print("✓ Initial parameters sent")
            else:
                self.status_label.setText("● Connection Failed")
                self.status_label.setStyleSheet("color: red;")
        else:
            self.osc_connected = False
            self.connect_btn.setText("Connect SuperCollider")
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: orange;")
            self.mixer_panel.set_io_status(audio=False)
            
    def on_parameter_changed(self, param_id, value):
        """Handle global modulation parameter change."""
        if self.osc_connected:
            self.osc.send_parameter(param_id, value)
        print(f"{param_id}: {value:.3f}")
        
    def on_generator_param_changed(self, slot_id, param_name, value):
        """Handle per-generator parameter change."""
        if self.osc_connected:
            self.osc.client.send_message(f"/noise/gen/{param_name}", [slot_id, value])
        print(f"Gen {slot_id} {param_name}: {value:.3f}")
        
    def on_generator_filter_changed(self, slot_id, filter_type):
        """Handle generator filter type change."""
        filter_map = {"LP": 0, "HP": 1, "BP": 2}
        if self.osc_connected:
            self.osc.client.send_message("/noise/gen/filterType", [slot_id, filter_map[filter_type]])
        print(f"Gen {slot_id} filter: {filter_type}")
        
    def on_generator_clock_changed(self, slot_id, clock_div):
        """Handle generator clock routing change."""
        print(f"Gen {slot_id} clock: {clock_div}")
        
    def on_generator_selected(self, slot_id):
        """Handle generator slot selection."""
        print(f"Generator {slot_id} selected")
        
        current_type = self.generator_grid.get_slot(slot_id).generator_type
        
        if current_type == "Empty":
            new_type = "Test Synth"
            synth_name = "testSynth"
        elif current_type == "Test Synth":
            new_type = "PT2399"
            synth_name = "pt2399Grainy"
        elif current_type == "PT2399":
            new_type = "Empty"
            synth_name = None
        else:
            new_type = "Empty"
            synth_name = None
        
        self.generator_grid.set_generator_type(slot_id, new_type)
        
        if synth_name:
            if self.osc_connected:
                self.osc.client.send_message("/noise/start_generator", [slot_id, synth_name])
                print(f"Started {new_type} in slot {slot_id}")
            
            self.generator_grid.set_generator_active(slot_id, True)
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(True)
            self.active_generators[slot_id] = synth_name
        else:
            if self.osc_connected:
                self.osc.client.send_message("/noise/stop_generator", [slot_id])
                print(f"Stopped generator in slot {slot_id}")
            
            self.generator_grid.set_generator_active(slot_id, False)
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(False)
            if slot_id in self.active_generators:
                del self.active_generators[slot_id]
                
    def on_effect_selected(self, slot_id):
        """Handle effect slot selection."""
        print(f"Effect slot {slot_id} selected")
        
        current_type = self.effects_chain.get_slot(slot_id).effect_type
        
        if current_type == "Empty":
            new_type = "Fidelity"
            slot = self.effects_chain.get_slot(slot_id)
            slot.set_amount(0.75)
            self.active_effects[slot_id] = new_type
            if self.osc_connected:
                self.osc.client.send_message("/noise/fidelity_amount", [0.75])
                print(f"Activated {new_type} at 75%")
        elif current_type == "Fidelity":
            new_type = "Empty"
            if slot_id in self.active_effects:
                del self.active_effects[slot_id]
            if self.osc_connected:
                self.osc.client.send_message("/noise/fidelity_amount", [1.0])
                print(f"Fidelity passthrough (100%)")
        else:
            new_type = "Empty"
        
        self.effects_chain.set_effect_type(slot_id, new_type)
            
    def on_effect_amount_changed(self, slot_id, amount):
        """Handle effect amount change."""
        print(f"Effect {slot_id} amount: {amount:.2f}")
        if self.osc_connected and slot_id in self.active_effects:
            self.osc.client.send_message("/noise/fidelity_amount", [amount])
        
    def on_generator_volume_changed(self, gen_id, volume):
        """Handle generator volume change."""
        print(f"Generator {gen_id} volume: {volume:.2f}")
        
    def on_generator_muted(self, gen_id, muted):
        """Handle generator mute."""
        print(f"Generator {gen_id} {'muted' if muted else 'unmuted'}")
        
    def on_generator_solo(self, gen_id, solo):
        """Handle generator solo."""
        print(f"Generator {gen_id} {'solo' if solo else 'unsolo'}")
        
    def on_master_volume_changed(self, volume):
        """Handle master volume change."""
        print(f"Master volume: {volume:.2f}")
