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
    # Initialize logger first
    from src.utils.logger import logger
    
    logger.info("=" * 40, component="APP")
    logger.info("Noise Engine starting", component="APP")
    logger.info("=" * 40, component="APP")
    logger.info("1. Start SuperCollider and run init.scd", component="APP")
    logger.info("2. Click 'Connect SuperCollider' in the app", component="APP")
    logger.info("3. Click generator slots to start sounds", component="APP")
    logger.info("4. Click effect slots to add effects", component="APP")
    logger.info("=" * 40, component="APP")
    
    app = QApplication(sys.argv)
    
    from src.gui.main_frame import MainFrame
    
    window = MainFrame()
    
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
