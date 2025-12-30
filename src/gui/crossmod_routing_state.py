"""
Crossmod Routing State
State management for generator-to-generator cross-modulation routing.

Holds all crossmod connections and follower states, emits signals on changes.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal


@dataclass
class CrossmodConnection:
    """A single crossmod routing connection."""
    source_gen: int       # 1-8 (source generator)
    target_gen: int       # 1-8 (target generator)
    target_param: str     # 'cutoff', 'resonance', 'frequency', 'attack', 'decay', 'p1'-'p5'
    amount: float = 0.5   # 0.0 - 1.0 (VCA level)
    offset: float = 0.0   # -1.0 to 1.0 (shifts mod range)
    invert: bool = False  # True = inverted (for ducking)
    
    # v1 fixed values (not exposed in UI)
    depth: float = 1.0    # Range width (fixed at 1.0 for v1)
    polarity: int = 0     # 0=bipolar (fixed for v1)


@dataclass
class FollowerState:
    """Envelope follower state for a source generator."""
    enabled: bool = True
    attack_s: float = 0.01   # v2: will be exposed
    release_s: float = 0.1   # v2: will be exposed


class CrossmodRoutingState(QObject):
    """
    Central state for all crossmod routing.
    
    Signals:
        connection_added(CrossmodConnection): New connection created
        connection_removed(source_gen, target_gen, target_param): Connection deleted
        connection_changed(CrossmodConnection): Connection parameters modified
        follower_changed(source_gen): Follower state changed
        all_cleared(): All connections removed
    """
    
    # Signals
    connection_added = pyqtSignal(object)      # CrossmodConnection
    connection_removed = pyqtSignal(int, int, str)  # source, target, param
    connection_changed = pyqtSignal(object)    # CrossmodConnection
    follower_changed = pyqtSignal(int)         # source_gen
    all_cleared = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Connections keyed by (source_gen, target_gen, target_param)
        self._connections: Dict[Tuple[int, int, str], CrossmodConnection] = {}
        
        # Follower state per source generator (1-8)
        self._followers: Dict[int, FollowerState] = {
            i: FollowerState() for i in range(1, 9)
        }
        
        # Prior states for toggle restore
        self._prior_states: Dict[Tuple[int, int, str], CrossmodConnection] = {}
    
    # === Connection Methods ===
    
    def add_connection(self, conn: CrossmodConnection):
        """Add or update a connection."""
        key = (conn.source_gen, conn.target_gen, conn.target_param)
        self._connections[key] = conn
        self.connection_added.emit(conn)
    
    def remove_connection(self, source_gen: int, target_gen: int, target_param: str):
        """Remove a connection, storing prior state for restore."""
        key = (source_gen, target_gen, target_param)
        if key in self._connections:
            # Store for restore on re-toggle
            self._prior_states[key] = self._connections[key]
            del self._connections[key]
            self.connection_removed.emit(source_gen, target_gen, target_param)
    
    def get_connection(self, source_gen: int, target_gen: int, target_param: str) -> Optional[CrossmodConnection]:
        """Get connection if it exists."""
        key = (source_gen, target_gen, target_param)
        return self._connections.get(key)
    
    def get_prior_state(self, source_gen: int, target_gen: int, target_param: str) -> Optional[CrossmodConnection]:
        """Get prior state for restore on re-toggle."""
        key = (source_gen, target_gen, target_param)
        return self._prior_states.get(key)
    
    def get_all_connections(self):
        """Iterate all connections."""
        return self._connections.values()
    
    def update_connection(self, source_gen: int, target_gen: int, target_param: str,
                          amount: float = None, offset: float = None, invert: bool = None):
        """Update specific fields of an existing connection."""
        key = (source_gen, target_gen, target_param)
        conn = self._connections.get(key)
        if conn:
            if amount is not None:
                conn.amount = amount
            if offset is not None:
                conn.offset = offset
            if invert is not None:
                conn.invert = invert
            self.connection_changed.emit(conn)
    
    def set_amount(self, source_gen: int, target_gen: int, target_param: str, amount: float):
        """Set amount for a connection."""
        self.update_connection(source_gen, target_gen, target_param, amount=amount)
    
    def set_offset(self, source_gen: int, target_gen: int, target_param: str, offset: float):
        """Set offset for a connection."""
        self.update_connection(source_gen, target_gen, target_param, offset=offset)
    
    def set_invert(self, source_gen: int, target_gen: int, target_param: str, invert: bool):
        """Set invert for a connection."""
        self.update_connection(source_gen, target_gen, target_param, invert=invert)
    
    def toggle_invert(self, source_gen: int, target_gen: int, target_param: str):
        """Toggle invert state for a connection."""
        conn = self.get_connection(source_gen, target_gen, target_param)
        if conn:
            self.set_invert(source_gen, target_gen, target_param, not conn.invert)
    
    def clear(self):
        """Clear all connections."""
        self._connections.clear()
        self.all_cleared.emit()
    
    # === Follower Methods ===
    
    @property
    def followers(self) -> Dict[int, FollowerState]:
        """Access follower states."""
        return self._followers
    
    def set_follower_enabled(self, source_gen: int, enabled: bool):
        """Enable/disable follower for a source generator."""
        if 1 <= source_gen <= 8:
            self._followers[source_gen].enabled = enabled
            self.follower_changed.emit(source_gen)
    
    def is_follower_enabled(self, source_gen: int) -> bool:
        """Check if follower is enabled for a source."""
        if 1 <= source_gen <= 8:
            return self._followers[source_gen].enabled
        return False
