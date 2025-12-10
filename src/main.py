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


def main():
    print("=" * 50)
    print("Noise Engine")
    print("=" * 50)
    print("1. Start SuperCollider and run init.scd")
    print("2. Click 'Connect SuperCollider' in the app")
    print("3. Use modulation sliders to control sound")
    print("4. Click generator slots to cycle types")
    print("=" * 50)
    
    # Create app first
    app = QApplication(sys.argv)
    
    # Now we can import MainFrame (after QApplication exists)
    from src.gui.main_frame import MainFrame
    
    # Create main window
    window = MainFrame()
    
    # Set up PT2399 generator (matches what's in SuperCollider)
    window.set_pt2399_generator()
    
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
