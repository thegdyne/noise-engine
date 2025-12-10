"""
Main entry point for the Noise Engine.
Launches the main frame with all components.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


def main():
    print("=" * 50)
    print("Noise Engine")
    print("=" * 50)
    print("1. Start SuperCollider and run init.scd")
    print("2. Click 'Connect SuperCollider' in the app")
    print("3. Click generator slots to start sounds")
    print("4. Click effect slots to add effects")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    from src.gui.main_frame import MainFrame
    
    window = MainFrame()
    
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
