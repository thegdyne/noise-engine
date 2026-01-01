"""
Test the Mixer Panel component standalone
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from src.gui.mixer_panel import MixerPanel


def main():
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Mixer Panel Test")
    window.setGeometry(100, 100, 400, 600)
    
    # Create mixer
    mixer = MixerPanel(num_generators=8)
    
    # Connect signals
    mixer.generator_volume_changed.connect(
        lambda gen_id, vol: print(f"Gen {gen_id} volume: {vol:.2f}")
    )
    mixer.generator_muted.connect(
        lambda gen_id, muted: print(f"Gen {gen_id} muted: {muted}")
    )
    mixer.generator_solo.connect(
        lambda gen_id, solo: print(f"Gen {gen_id} solo: {solo}")
    )
    mixer.master_volume_changed.connect(
        lambda vol: print(f"Master volume: {vol:.2f}")
    )
    
    # Set some test I/O status
    mixer.set_io_status(audio=True, midi=False, cv=False)
    
    window.setCentralWidget(mixer)
    window.show()
    
    print("=" * 50)
    print("Mixer Panel Test")
    print("=" * 50)
    print("- Move faders to test volume control")
    print("- Click M/S buttons to test mute/solo")
    print("- Resize window vertically to test fader scaling")
    print("=" * 50)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
