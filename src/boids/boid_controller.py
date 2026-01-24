"""
Boid Controller - Manages boid simulation and OSC communication

Connects:
- BoidEngine (simulation physics)
- BoidState (persistent state)
- BoidBusSender (OSC protocol for unified buses)
- Generator routing (separate OSC path for cols 0-79)

Runs simulation at 20Hz via QTimer.
"""

from typing import Optional, List, Tuple, Callable
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from src.utils.logger import logger

from .boid_engine import BoidEngine, SIM_HZ
from .boid_state import BoidState, generate_random_seed
from ..utils.boid_bus import BoidBusSender


class BoidController(QObject):
    """
    Controller for boid modulation system.

    Manages simulation lifecycle, state persistence, and OSC communication.
    Emits signals for UI updates.
    """

    # Signals for UI
    positions_updated = pyqtSignal(list)  # List of (x, y) tuples
    cells_updated = pyqtSignal(dict)      # Dict of (row, col) -> value
    seed_changed = pyqtSignal(int)
    enabled_changed = pyqtSignal(bool)

    def __init__(self, main_frame, parent=None):
        super().__init__(parent)

        self._main = main_frame
        self._bus_sender: Optional[BoidBusSender] = None

        # Core components
        self._engine = BoidEngine()
        self._state = BoidState()

        # Generator routing callback (set by modulation controller)
        self._gen_route_callback: Optional[Callable] = None

        # Simulation timer (50ms = 20Hz)
        self._timer = QTimer(self)
        self._timer.setInterval(1000 // SIM_HZ)
        self._timer.timeout.connect(self._tick)

        # Wire zone filter to engine
        self._engine.set_cell_filter(self._state.is_cell_allowed)

    def _get_bus_sender(self) -> Optional[BoidBusSender]:
        """Get or create bus sender (lazy init after OSC connects)."""
        if self._bus_sender is None and self._main.osc_connected:
            self._bus_sender = BoidBusSender(self._main.osc.client)
        return self._bus_sender

    @property
    def engine(self) -> BoidEngine:
        """Access to engine for visualization."""
        return self._engine

    @property
    def state(self) -> BoidState:
        """Access to state for serialization."""
        return self._state

    def set_gen_route_callback(self, callback: Callable) -> None:
        """
        Set callback for generator routing (cols 0-79).

        Callback signature: callback(contributions: List[Tuple[row, col, value]])
        """
        self._gen_route_callback = callback

    # === Lifecycle ===

    def start(self) -> None:
        """Start boid simulation."""
        if self._state.enabled:
            return

        # Check OSC connection
        if not self._main.osc_connected:
            from src.utils.logger import logger
            logger.warning("Cannot start boids: OSC not connected", component="BOID")
            return

        # Get seed
        seed = self._state.get_active_seed()
        self.seed_changed.emit(self._state.seed)

        # Initialize engine
        self._engine.set_boid_count(self._state.boid_count)
        self._engine.set_dispersion(self._state.dispersion)
        self._engine.set_energy(self._state.energy)
        self._engine.set_fade(self._state.fade)
        self._engine.set_depth(self._state.depth)
        self._engine.initialize(seed)

        # Enable bus sender
        bus_sender = self._get_bus_sender()
        if bus_sender:
            bus_sender.enable()

        # Start timer
        self._timer.start()

        self._state.enabled = True
        self.enabled_changed.emit(True)

    def stop(self) -> None:
        """Stop boid simulation."""
        if not self._state.enabled:
            return

        # Stop timer
        self._timer.stop()

        # Disable bus sender (sends clear)
        bus_sender = self._get_bus_sender()
        if bus_sender:
            bus_sender.disable()

        # Clear generator routes if callback set
        if self._gen_route_callback:
            self._gen_route_callback([])

        # Reset engine
        self._engine.reset()

        self._state.enabled = False
        self.enabled_changed.emit(False)

    def toggle(self) -> None:
        """Toggle enabled state."""
        if self._state.enabled:
            self.stop()
        else:
            self.start()

    def _tick(self) -> None:
        """Simulation tick (called at 20Hz)."""
        # Track tick count for debugging
        if not hasattr(self, '_tick_count'):
            self._tick_count = 0
            logger.info("Boid timer firing", component="BOID")
        self._tick_count += 1

        if not self._state.enabled:
            return

        # Advance simulation
        self._engine.tick()

        # Get contributions
        contributions = self._engine.get_contributions()

        # Debug: log contribution counts every second
        if self._tick_count % 20 == 0:
            gen_count = sum(1 for r, c, v in contributions if c < 80)
            unified_count = sum(1 for r, c, v in contributions if c >= 80)
            logger.info(f"Boid tick {self._tick_count}: {len(contributions)} total ({gen_count} GEN, {unified_count} unified)", component="BOID")

        # Split by column range
        gen_contributions = []
        unified_contributions = []

        for row, col, value in contributions:
            if col < 80:
                gen_contributions.append((row, col, value))
            else:
                unified_contributions.append((row, col, value))

        # Send unified bus offsets
        bus_sender = self._get_bus_sender()
        if bus_sender:
            bus_sender.send_offsets(unified_contributions)

        # Send generator routes if callback set
        if self._gen_route_callback and gen_contributions:
            self._gen_route_callback(gen_contributions)

        # Emit signals for visualization
        self.positions_updated.emit(self._engine.get_positions())
        self.cells_updated.emit(self._engine.get_cell_values())

    # === Parameter setters ===

    def set_boid_count(self, count: int) -> None:
        """Set number of boids."""
        self._state.boid_count = count
        self._engine.set_boid_count(count)

    def set_dispersion(self, value: float) -> None:
        """Set dispersion (0-1)."""
        self._state.dispersion = value
        self._engine.set_dispersion(value)

    def set_energy(self, value: float) -> None:
        """Set energy (0-1)."""
        self._state.energy = value
        self._engine.set_energy(value)

    def set_fade(self, value: float) -> None:
        """Set fade time (0-1)."""
        self._state.fade = value
        self._engine.set_fade(value)

    def set_depth(self, value: float) -> None:
        """Set connection depth (0-1)."""
        self._state.depth = value
        self._engine.set_depth(value)

    # === Zone control ===

    def set_zone_gen(self, enabled: bool) -> None:
        """Enable/disable generator zone (cols 0-79)."""
        self._state.zone_gen = enabled

    def set_zone_mod(self, enabled: bool) -> None:
        """Enable/disable mod zone (cols 80-107)."""
        self._state.zone_mod = enabled

    def set_zone_chan(self, enabled: bool) -> None:
        """Enable/disable channel zone (cols 108-131)."""
        self._state.zone_chan = enabled

    def set_zone_fx(self, enabled: bool) -> None:
        """Enable/disable FX zone (cols 132-150)."""
        self._state.zone_fx = enabled

    # === Row control ===

    def set_row_slot1(self, enabled: bool) -> None:
        """Enable/disable row slot 1 (rows 0-3)."""
        self._state.row_slot1 = enabled

    def set_row_slot2(self, enabled: bool) -> None:
        """Enable/disable row slot 2 (rows 4-7)."""
        self._state.row_slot2 = enabled

    def set_row_slot3(self, enabled: bool) -> None:
        """Enable/disable row slot 3 (rows 8-11)."""
        self._state.row_slot3 = enabled

    def set_row_slot4(self, enabled: bool) -> None:
        """Enable/disable row slot 4 (rows 12-15)."""
        self._state.row_slot4 = enabled

    # === Behavior presets ===

    def apply_preset(self, preset_name: str) -> None:
        """Apply a behavior preset (sets dispersion/energy/fade)."""
        if self._state.apply_behavior_preset(preset_name):
            # Update engine with new values
            self._engine.set_dispersion(self._state.dispersion)
            self._engine.set_energy(self._state.energy)
            self._engine.set_fade(self._state.fade)

    # === Seed control ===

    def set_seed_locked(self, locked: bool) -> None:
        """Lock/unlock seed for deterministic playback."""
        self._state.seed_locked = locked

    def reseed(self) -> None:
        """Generate new random seed and restart if running."""
        self._state.seed = generate_random_seed()
        self.seed_changed.emit(self._state.seed)

        if self._state.enabled:
            # Reinitialize with new seed
            self._engine.initialize(self._state.seed)

    # === State persistence ===

    def get_state_dict(self) -> dict:
        """Get state for preset saving."""
        return self._state.to_dict()

    def load_state_dict(self, data: dict) -> None:
        """Load state from preset."""
        was_enabled = self._state.enabled
        if was_enabled:
            self.stop()

        self._state = BoidState.from_dict(data)

        # Re-wire zone filter
        self._engine.set_cell_filter(self._state.is_cell_allowed)

        # Restore parameters to engine
        self._engine.set_boid_count(self._state.boid_count)
        self._engine.set_dispersion(self._state.dispersion)
        self._engine.set_energy(self._state.energy)
        self._engine.set_fade(self._state.fade)
        self._engine.set_depth(self._state.depth)

        # Emit seed
        self.seed_changed.emit(self._state.seed)

        # Resume if was enabled or state says enabled
        if was_enabled or self._state.enabled:
            self.start()

    def reset_to_defaults(self) -> None:
        """Reset to default state."""
        was_enabled = self._state.enabled
        if was_enabled:
            self.stop()

        self._state = BoidState()
        self._engine.set_cell_filter(self._state.is_cell_allowed)
        self.seed_changed.emit(self._state.seed)
