"""
Test the Generator Grid component standalone
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from src.gui.generator_grid import GeneratorGrid


def main():
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Generator Grid Test")
    window.setGeometry(100, 100, 800, 600)
    
    # Create grid
    grid = GeneratorGrid(rows=2, cols=4)
    
    # Set some test generators
    grid.set_generator_type(1, "PT2399")
    grid.set_generator_active(1, True)
    
    grid.set_generator_type(2, "Sampler")
    grid.set_generator_type(3, "Clicks")
    
    # Connect signal
    grid.generator_selected.connect(
        lambda slot_id: print(f"Selected generator {slot_id}")
    )
    
    window.setCentralWidget(grid)
    window.show()
    
    print("=" * 50)
    print("Generator Grid Test")
    print("=" * 50)
    print("- Resize window to test responsiveness")
    print("- Click slots to test selection")
    print("- Gen 1 should be active (green border)")
    print("=" * 50)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
