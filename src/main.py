"""
Main entry point for the Noise Engine.
Launches the main frame with all components.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from src.gui.main_frame import MainFrame


def main():
    print("=" * 50)
    print("Noise Engine")
    print("=" * 50)
    print("1. Start SuperCollider and run init.scd")
    print("2. Click 'Connect SuperCollider' in the app")
    print("3. Use modulation sliders to control sound")
    print("4. Adjust generator volumes in mixer")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    # Enable high DPI
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create main window
    window = MainFrame()
    
    # Set up test generator
    window.set_test_generator()
    
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
