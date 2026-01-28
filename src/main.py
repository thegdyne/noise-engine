"""
Main entry point for the Noise Engine.
Launches the main frame with all components.
"""

import sys
import os
import signal
import time
import atexit

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


def cleanup_sc():
    """Gracefully stop SuperCollider."""
    # Stop OSC server first (prevents "deleted object" errors)
    try:
        from src.audio.osc_bridge import osc_bridge
        if osc_bridge:
            osc_bridge.stop()
    except Exception:  # Expected during shutdown - OSC may already be gone
        pass

    # Fade master volume
    try:
        from pythonosc import udp_client
        client = udp_client.SimpleUDPClient("127.0.0.1", 57120)
        client.send_message("/noise/quit", [])  # Tell SC to stop sending to Python
        client.send_message("/ne/master/volume", 0.0)
        time.sleep(0.15)
    except Exception:  # Expected during shutdown - SC may not be running
        pass

    # Kill only the sclang instance spawned by NoiseEngine (recorded by tools/ne-run).
    try:
        from src.utils.app_paths import get_sc_pid_path
        pid_path = get_sc_pid_path()
        if not pid_path.exists():
            return
        raw = pid_path.read_text().strip()
        pid = int(raw) if raw else 0
        if pid <= 0:
            pid_path.unlink(missing_ok=True)
            return
        # Is it alive?
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pid_path.unlink(missing_ok=True)
            return
        os.kill(pid, signal.SIGTERM)
        # Wait briefly for graceful exit
        deadline = time.time() + 0.75
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pid_path.unlink(missing_ok=True)
                return
            time.sleep(0.05)
        # Last resort
        os.kill(pid, signal.SIGKILL)
        pid_path.unlink(missing_ok=True)
    except Exception:
        # Never let shutdown raise
        pass

    # Hard reset fallback - kill any remaining SC processes
    try:
        import subprocess
        subprocess.run(["pkill", "-9", "-f", "sclang"], capture_output=True)
        subprocess.run(["pkill", "-9", "-f", "scsynth"], capture_output=True)
        time.sleep(0.5)
    except Exception:  # Expected during shutdown - pkill may not exist on all platforms
        pass


def signal_handler(signum, frame):
    """Handle SIGTERM/SIGINT - cleanup then exit."""
    cleanup_sc()
    sys.exit(0)


def main():
    # Register SC cleanup handlers
    atexit.register(cleanup_sc)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

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
    app.setOrganizationName("NoiseEngine")
    app.setApplicationName("NoiseEngine")

    from src.gui.main_frame import MainFrame
    
    window = MainFrame()
    
    # Install F9 hotkey for layout debug toggle
    from src.gui.layout_debug import install_debug_hotkey
    install_debug_hotkey(window)
    
    # Enable layout debug overlay if DEBUG_LAYOUT=1
    if os.environ.get('DEBUG_LAYOUT', '0') == '1':
        from src.gui.layout_debug import enable_layout_debug
        logger.info("Layout debug mode ENABLED", component="APP")
        enable_layout_debug(window)
    
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
