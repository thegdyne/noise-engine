"""
Main Frame - Combines all components
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QShortcut, QStackedLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence

from src.gui.generator_grid import GeneratorGrid
from src.gui.mixer_panel import MixerPanel
from src.gui.master_section import MasterSection
from src.gui.effects_chain import EffectsChain
from src.gui.modulation_sources import ModulationSources
from src.gui.bpm_display import BPMDisplay
from src.gui.midi_selector import MIDISelector
from src.gui.console_panel import ConsolePanel
from src.gui.theme import COLORS, button_style, FONT_FAMILY, FONT_SIZES
from src.audio.osc_bridge import OSCBridge
from src.config import (
    CLOCK_RATE_INDEX, FILTER_TYPE_INDEX, GENERATORS, GENERATOR_CYCLE,
    BPM_DEFAULT, OSC_PATHS
)
from src.utils.logger import logger


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
        
        # Content area with console overlay
        content_container = QWidget()
        content_outer = QHBoxLayout(content_container)
        content_outer.setContentsMargins(0, 0, 0, 0)
        content_outer.setSpacing(0)
        
        # Main content (left side)
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
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
        self.generator_grid.generator_env_source_changed.connect(self.on_generator_env_source)
        self.generator_grid.generator_clock_rate_changed.connect(self.on_generator_clock_rate)
        self.generator_grid.generator_mute_changed.connect(self.on_generator_mute)
        self.generator_grid.generator_midi_channel_changed.connect(self.on_generator_midi_channel)
        content_layout.addWidget(self.generator_grid, stretch=5)
        
        # Right - MIXER + MASTER (stacked vertically)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Mixer (upper portion)
        self.mixer_panel = MixerPanel(num_generators=8)
        self.mixer_panel.generator_volume_changed.connect(self.on_generator_volume_changed)
        self.mixer_panel.generator_muted.connect(self.on_generator_muted)
        self.mixer_panel.generator_solo.connect(self.on_generator_solo)
        right_layout.addWidget(self.mixer_panel, stretch=2)
        
        # Master section (lower portion)
        self.master_section = MasterSection()
        self.master_section.master_volume_changed.connect(self.on_master_volume_from_master)
        right_layout.addWidget(self.master_section, stretch=1)
        
        content_layout.addWidget(right_panel, stretch=1)
        
        content_outer.addWidget(content_widget, stretch=1)
        
        # Console panel (right edge overlay)
        self.console_panel = ConsolePanel()
        content_outer.addWidget(self.console_panel)
        
        main_layout.addWidget(content_container, stretch=1)
        
        # Bottom - EFFECTS only
        bottom_section = self.create_bottom_section()
        main_layout.addWidget(bottom_section)
        
        # Keyboard shortcut for console (Cmd+` or Ctrl+`)
        console_shortcut = QShortcut(QKeySequence("Ctrl+`"), self)
        console_shortcut.activated.connect(self.toggle_console)
        
        # Log startup
        logger.info("Noise Engine started", component="APP")
        
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
        
        layout.addSpacing(20)
        
        # MIDI device selector
        self.midi_selector = MIDISelector()
        self.midi_selector.device_changed.connect(self.on_midi_device_changed)
        layout.addWidget(self.midi_selector)
        
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
        
        layout.addSpacing(10)
        
        # Console toggle button
        self.console_btn = QPushButton(">_")
        self.console_btn.setToolTip("Toggle Console (Ctrl+`)")
        self.console_btn.setFixedSize(30, 30)
        self.console_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                font-family: {FONT_FAMILY};
                font-size: {FONT_SIZES['small']}px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['background_highlight']};
                color: {COLORS['text_bright']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['enabled']};
                color: {COLORS['enabled_text']};
                border-color: {COLORS['enabled']};
            }}
        """)
        self.console_btn.setCheckable(True)
        self.console_btn.clicked.connect(self.toggle_console)
        layout.addWidget(self.console_btn)
        
        # Restart button
        self.restart_btn = QPushButton("↻")
        self.restart_btn.setToolTip("Restart Noise Engine")
        self.restart_btn.setFixedSize(30, 30)
        self.restart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                font-size: {FONT_SIZES['section']}px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['submenu']};
                color: {COLORS['submenu_text']};
                border-color: {COLORS['submenu']};
            }}
        """)
        self.restart_btn.clicked.connect(self.restart_app)
        layout.addWidget(self.restart_btn)
        
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
            # Connect signals before connecting
            self.osc.gate_triggered.connect(self.on_gate_trigger)
            self.osc.levels_received.connect(self.on_levels_received)
            self.osc.connection_lost.connect(self.on_connection_lost)
            self.osc.connection_restored.connect(self.on_connection_restored)
            
            if self.osc.connect():
                self.osc_connected = True
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("● Connected")
                self.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
                self.mixer_panel.set_io_status(audio=True)
                
                self.osc.client.send_message(OSC_PATHS['clock_bpm'], [self.master_bpm])
                self.modulation_sources.set_master_bpm(self.master_bpm)
                
                # Send initial master volume
                self.osc.client.send_message(OSC_PATHS['master_volume'], [self.master_section.get_volume()])
                
                # Send current MIDI device if one is selected
                current_midi = self.midi_selector.get_current_device()
                if current_midi:
                    port_index = self.midi_selector.get_port_index(current_midi)
                    if port_index >= 0:
                        self.osc.client.send_message(OSC_PATHS['midi_device'], [port_index])
            else:
                self.status_label.setText("● Connection Failed")
                self.status_label.setStyleSheet(f"color: {COLORS['warning_text']};")
        else:
            try:
                self.osc.gate_triggered.disconnect(self.on_gate_trigger)
                self.osc.connection_lost.disconnect(self.on_connection_lost)
                self.osc.connection_restored.disconnect(self.on_connection_restored)
            except TypeError:
                pass  # Signals weren't connected
            self.osc.disconnect()
            self.osc_connected = False
            self.connect_btn.setText("Connect SuperCollider")
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet(f"color: {COLORS['submenu_text']};")
            self.mixer_panel.set_io_status(audio=False)
    
    def on_connection_lost(self):
        """Handle connection lost - show prominent warning."""
        self.osc_connected = False
        self.connect_btn.setText("⚠ RECONNECT")
        self.connect_btn.setStyleSheet(f"background-color: {COLORS['warning_text']}; color: black; font-weight: bold;")
        self.status_label.setText("● CONNECTION LOST")
        self.status_label.setStyleSheet(f"color: {COLORS['warning_text']}; font-weight: bold;")
        self.mixer_panel.set_io_status(audio=False)
    
    def on_connection_restored(self):
        """Handle connection restored after reconnect."""
        self.osc_connected = True
        self.connect_btn.setText("Disconnect")
        self.connect_btn.setStyleSheet("")  # Reset to default style
        self.status_label.setText("● Connected")
        self.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
        self.mixer_panel.set_io_status(audio=True)
        
        # Resend current state
        self.osc.client.send_message(OSC_PATHS['clock_bpm'], [self.master_bpm])
    
    def on_gate_trigger(self, slot_id):
        """Handle gate trigger from SC - flash LED."""
        slot = self.generator_grid.get_slot(slot_id)
        if slot:
            slot.flash_gate()
    
    def on_midi_device_changed(self, device_name):
        """Handle MIDI device selection change."""
        if self.osc_connected:
            if device_name:
                port_index = self.midi_selector.get_port_index(device_name)
                if port_index >= 0:
                    self.osc.client.send_message(OSC_PATHS['midi_device'], [port_index])
                    logger.info(f"MIDI device: {device_name} (port {port_index})", component="MIDI")
            else:
                self.osc.client.send_message(OSC_PATHS['midi_device'], [-1])  # -1 = disconnect
                logger.info("MIDI device: None", component="MIDI")
        
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
        """Handle generator envelope ON/OFF (legacy)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_env_enabled'], [slot_id, 1 if enabled else 0])
    
    def on_generator_env_source(self, slot_id, source):
        """Handle generator ENV source change (0=OFF, 1=CLK, 2=MIDI)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_env_source'], [slot_id, source])
        logger.gen(slot_id, f"env source: {['OFF', 'CLK', 'MIDI'][source]}")
        
    def on_generator_clock_rate(self, slot_id, rate):
        """Handle generator clock rate change - send index."""
        rate_index = CLOCK_RATE_INDEX.get(rate, 3)  # Default to CLK
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_clock_rate'], [slot_id, rate_index])
        logger.gen(slot_id, f"rate: {rate} (index {rate_index})")
    
    def on_generator_mute(self, slot_id, muted):
        """Handle generator mute from slot button."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_mute'], [slot_id, 1 if muted else 0])
        logger.gen(slot_id, f"mute: {muted}")
    
    def on_generator_midi_channel(self, slot_id, channel):
        """Handle generator MIDI channel change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_midi_channel'], [slot_id, channel])
        logger.gen(slot_id, f"MIDI channel: {channel}")
        
    def on_generator_selected(self, slot_id):
        """Handle generator slot selection (legacy click handler)."""
        # Legacy - cycles through generators on click
        # New behavior uses on_generator_changed from CycleButton
        pass
    
    def on_generator_changed(self, slot_id, new_type):
        """Handle generator type change from CycleButton."""
        from src.config import get_generator_midi_retrig
        
        synth_name = GENERATORS.get(new_type)
        
        # Update the slot (custom params, etc)
        self.generator_grid.set_generator_type(slot_id, new_type)
        
        if synth_name:
            if self.osc_connected:
                self.osc.client.send_message(OSC_PATHS['start_generator'], [slot_id, synth_name])
                # Tell SC if this generator needs MIDI retriggering
                midi_retrig = 1 if get_generator_midi_retrig(new_type) else 0
                self.osc.client.send_message(OSC_PATHS['midi_retrig'], [slot_id, midi_retrig])
            
            self.generator_grid.set_generator_active(slot_id, True)
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(True)
            self.active_generators[slot_id] = synth_name
            
            # Update mixer channel active state
            self.mixer_panel.set_channel_active(slot_id, True)
        else:
            if self.osc_connected:
                self.osc.client.send_message(OSC_PATHS['stop_generator'], [slot_id])
                # Clear midi_retrig flag
                self.osc.client.send_message(OSC_PATHS['midi_retrig'], [slot_id, 0])
            
            self.generator_grid.set_generator_active(slot_id, False)
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(False)
            if slot_id in self.active_generators:
                del self.active_generators[slot_id]
            
            # Update mixer channel active state
            self.mixer_panel.set_channel_active(slot_id, False)
                
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
        """Handle generator volume change from mixer."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_volume'], [gen_id, volume])
        logger.debug(f"Gen {gen_id} volume: {volume:.2f}", component="OSC")
        
    def on_generator_muted(self, gen_id, muted):
        """Handle generator mute from mixer."""
        if self.osc_connected:
	    self.osc.client.send_message(OSC_PATHS['gen_mute'], [gen_id, 1 if muted else 0])
        logger.debug(f"Gen {gen_id} mute: {muted}", component="OSC")
        
    def on_generator_solo(self, gen_id, solo):
        """Handle generator solo from mixer."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_strip_solo'], [gen_id, 1 if solo else 0])
        logger.debug(f"Gen {gen_id} solo: {solo}", component="OSC")
        
    def on_master_volume_from_master(self, volume):
        """Handle master volume change from master section."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_volume'], [volume])
        logger.info(f"Master volume: {volume:.2f}", component="OSC")
        
    def on_levels_received(self, amp_l, amp_r, peak_l, peak_r):
        """Handle level meter data from SuperCollider."""
        self.master_section.set_levels(amp_l, amp_r, peak_l, peak_r)
    
    def toggle_console(self):
        """Toggle console panel visibility."""
        self.console_panel.toggle_panel()
        self.console_btn.setChecked(self.console_panel.is_open)
    
    def restart_app(self):
        """Restart the application with confirmation."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt5.QtCore import Qt
        import sys
        import os
        
        # Custom styled dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Restart")
        dialog.setFixedSize(280, 120)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border_light']};
            }}
            QLabel {{
                color: {COLORS['text_bright']};
                font-size: {FONT_SIZES['section']}px;
            }}
            QPushButton {{
                background-color: {COLORS['background_highlight']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px 20px;
                font-size: {FONT_SIZES['small']}px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
                color: {COLORS['text_bright']};
            }}
            QPushButton#confirm {{
                background-color: {COLORS['submenu']};
                color: {COLORS['submenu_text']};
                border-color: {COLORS['submenu']};
            }}
            QPushButton#confirm:hover {{
                background-color: {COLORS['warning_text']};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 15)
        layout.setSpacing(20)
        
        label = QLabel("Restart Noise Engine?")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        no_btn = QPushButton("Cancel")
        no_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(no_btn)
        
        yes_btn = QPushButton("Restart")
        yes_btn.setObjectName("confirm")
        yes_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(yes_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        logger.info("Restarting Noise Engine...", component="APP")
        
        # Disconnect OSC cleanly
        if self.osc_connected:
            try:
                self.osc.disconnect()
            except Exception as e:
                logger.warning(f"OSC disconnect failed during restart: {e}", component="APP")
        
        # Get the command to restart
        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        
        # Restart the process
        os.execv(python, [python, script])
