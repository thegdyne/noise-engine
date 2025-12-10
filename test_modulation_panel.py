"""
Test the Modulation Panel component standalone
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from src.gui.modulation_panel import ModulationPanel


def main():
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Modulation Panel Test")
    window.setGeometry(100, 100, 300, 600)
    
    # Create modulation panel (uses parameters from config)
    mod_panel = ModulationPanel()
    
    # Connect signal
    mod_panel.parameter_changed.connect(
        lambda param_id, value: print(f"{param_id}: {value:.3f}")
    )
    
    window.setCentralWidget(mod_panel)
    window.show()
    
    print("=" * 50)
    print("Modulation Panel Test")
    print("=" * 50)
    print("- Move sliders to test parameter control")
    print("- Resize window vertically to test slider scaling")
    print("- Values print to console")
    print("=" * 50)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
