#!/usr/bin/env python3
"""
Layout Sandbox - Test generator/modulator slots in isolation.

Usage:
    python tools/layout_sandbox.py [--generator|--modulator] [--torture]

Features:
    - Resizable window to test different sizes
    - F9 toggles debug overlay
    - --torture mode tests long generator names
    - Instant iteration without running full app
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel
from PyQt5.QtCore import Qt

# Long names for torture testing
TORTURE_NAMES = [
    "Empty",
    "Subtractive (Resonant)",
    "FM + Waveshaper + Feedback",
    "Wavetable Morphing Synth",
    "Granular Texture Engine",
    "Physical Modeling String",
    "Additive Harmonic Series",
]


class LayoutSandbox(QMainWindow):
    def __init__(self, widget_type='generator', torture=False):
        super().__init__()
        self.widget_type = widget_type
        self.torture = torture
        self.torture_index = 0
        
        self.setWindowTitle(f"Layout Sandbox - {widget_type.title()}")
        self.setMinimumSize(200, 200)
        self.resize(400, 500)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Controls
        controls = QHBoxLayout()
        
        if torture:
            self.name_label = QLabel(f"Name: {TORTURE_NAMES[0]}")
            controls.addWidget(self.name_label)
            
            next_btn = QPushButton("Next Name")
            next_btn.clicked.connect(self.next_torture_name)
            controls.addWidget(next_btn)
        
        toggle_btn = QPushButton("Toggle Debug (F9)")
        toggle_btn.clicked.connect(self.toggle_debug)
        controls.addWidget(toggle_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # Create the test widget
        self.test_container = QWidget()
        self.test_layout = QVBoxLayout(self.test_container)
        self.test_layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.test_container, stretch=1)
        
        self.create_test_widget()
        
        # Install debug hotkey
        from gui.layout_debug import install_debug_hotkey
        install_debug_hotkey(self)
        
        # Status bar
        self.statusBar().showMessage("Press F9 to toggle layout debug overlay")
    
    def create_test_widget(self):
        """Create the slot widget being tested."""
        # Clear existing
        while self.test_layout.count():
            item = self.test_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self.widget_type == 'generator':
            from gui.generator_slot import GeneratorSlot
            self.slot = GeneratorSlot(1)
            self.test_layout.addWidget(self.slot)
            
            if self.torture:
                # Set torture name
                name = TORTURE_NAMES[self.torture_index]
                self.slot.type_btn.values = [name] + self.slot.type_btn.values[1:]
                self.slot.type_btn._update_display()
        else:
            from gui.modulator_slot import ModulatorSlot
            self.slot = ModulatorSlot(1)
            self.test_layout.addWidget(self.slot)
        
        self.test_layout.addStretch()
    
    def next_torture_name(self):
        """Cycle to next torture test name."""
        self.torture_index = (self.torture_index + 1) % len(TORTURE_NAMES)
        name = TORTURE_NAMES[self.torture_index]
        self.name_label.setText(f"Name: {name}")
        
        if self.widget_type == 'generator':
            self.slot.type_btn.values[0] = name
            self.slot.type_btn._update_display()
    
    def toggle_debug(self):
        """Toggle layout debug overlay."""
        from gui.layout_debug import toggle_layout_debug
        toggle_layout_debug()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Layout sandbox for testing slots')
    parser.add_argument('--generator', action='store_true', help='Test generator slot')
    parser.add_argument('--modulator', action='store_true', help='Test modulator slot')
    parser.add_argument('--torture', action='store_true', help='Enable long name torture test')
    args = parser.parse_args()
    
    widget_type = 'modulator' if args.modulator else 'generator'
    
    app = QApplication(sys.argv)
    
    window = LayoutSandbox(widget_type=widget_type, torture=args.torture)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
