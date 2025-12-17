"""
Mod Routing State
Data model for modulation connections between mod buses and generator parameters.

Each connection routes a mod bus output to a generator parameter with:
- amount: modulation range width (0-1)
- offset: shifts mod range up/down (-1 to +1)
- polarity: bipolar/uni+/uni-
- invert: flip mod signal before polarity
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal


class Polarity(Enum):
    """Modulation polarity modes."""
    BIPOLAR = 0   # Sweeps both above and below center
    UNI_POS = 1   # Only sweeps above center (positive)
    UNI_NEG = 2   # Only sweeps below center (negative)


@dataclass
class ModConnection:
    """A single modulation routing connection."""
    source_bus: int       # 0-15 (4 slots × 4 outputs)
    target_slot: int      # 1-8 (generator slot)
    target_param: str     # 'cutoff', 'frequency', 'resonance', etc.
    depth: float = 1.0    # Always 1.0 (kept for SC compat, not user-facing)
    amount: float = 0.5   # 0.0 to 1.0 (modulation range)
    offset: float = 0.0   # -1.0 to 1.0 (shifts mod range up/down)
    polarity: Polarity = Polarity.BIPOLAR
    invert: bool = False  # Flip signal before polarity
    
    @property
    def key(self) -> str:
        """Unique key for this connection."""
        return f"{self.source_bus}_{self.target_slot}_{self.target_param}"
    
    @property
    def effective_range(self) -> float:
        """Depth × Amount = actual modulation range."""
        return self.depth * self.amount
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for preset saving."""
        return {
            'source_bus': self.source_bus,
            'target_slot': self.target_slot,
            'target_param': self.target_param,
            'depth': self.depth,
            'amount': self.amount,
            'offset': self.offset,
            'polarity': self.polarity.value,
            'invert': self.invert,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModConnection':
        """Deserialize from dict with backward compatibility."""
        # Handle old format: negative depth = inverted
        old_depth = data.get('depth', 0.5)
        if old_depth < 0:
            depth = abs(old_depth)
            invert = True
        else:
            depth = old_depth
            invert = data.get('invert', False)
        
        # Handle old 'enabled' field (ignore, no longer used)
        # Connection exists = enabled; remove to disable
        
        return cls(
            source_bus=data['source_bus'],
            target_slot=data['target_slot'],
            target_param=data['target_param'],
            depth=depth,
            amount=data.get('amount', 1.0),
            offset=data.get('offset', 0.0),
            polarity=Polarity(data.get('polarity', 0)),
            invert=invert,
        )


class ModRoutingState(QObject):
    """
    Manages all modulation routing connections.
    
    Emits signals when connections change so UI and OSC can react.
    """
    
    # Signals
    connection_added = pyqtSignal(object)      # ModConnection
    connection_removed = pyqtSignal(int, int, str)  # source_bus, target_slot, target_param
    connection_changed = pyqtSignal(object)    # ModConnection (any field changed)
    all_cleared = pyqtSignal()                 # All connections removed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connections: Dict[str, ModConnection] = {}  # key -> connection
    
    def add_connection(self, conn: ModConnection) -> bool:
        """
        Add a new connection.
        
        Returns True if added, False if already exists.
        """
        if conn.key in self._connections:
            return False
        
        self._connections[conn.key] = conn
        self.connection_added.emit(conn)
        return True
    
    def remove_connection(self, source_bus: int, target_slot: int, target_param: str) -> bool:
        """
        Remove a connection.
        
        Returns True if removed, False if not found.
        """
        key = f"{source_bus}_{target_slot}_{target_param}"
        if key not in self._connections:
            return False
        
        del self._connections[key]
        self.connection_removed.emit(source_bus, target_slot, target_param)
        return True
    
    def get_connection(self, source_bus: int, target_slot: int, target_param: str) -> Optional[ModConnection]:
        """Get a specific connection, or None if not found."""
        key = f"{source_bus}_{target_slot}_{target_param}"
        return self._connections.get(key)
    
    def update_connection(self, source_bus: int, target_slot: int, target_param: str,
                          depth: Optional[float] = None,
                          amount: Optional[float] = None,
                          offset: Optional[float] = None,
                          polarity: Optional[Polarity] = None,
                          invert: Optional[bool] = None) -> bool:
        """
        Update connection parameters.
        
        Only updates fields that are not None.
        Returns True if updated, False if connection not found.
        """
        key = f"{source_bus}_{target_slot}_{target_param}"
        conn = self._connections.get(key)
        if conn is None:
            return False
        
        if depth is not None:
            conn.depth = max(0.0, min(1.0, depth))
        if amount is not None:
            conn.amount = max(0.0, min(1.0, amount))
        if offset is not None:
            conn.offset = max(-1.0, min(1.0, offset))
        if polarity is not None:
            conn.polarity = polarity
        if invert is not None:
            conn.invert = invert
        
        self.connection_changed.emit(conn)
        return True
    
    def set_depth(self, source_bus: int, target_slot: int, target_param: str, depth: float) -> bool:
        """Update connection depth (0-1)."""
        return self.update_connection(source_bus, target_slot, target_param, depth=depth)
    
    def set_amount(self, source_bus: int, target_slot: int, target_param: str, amount: float) -> bool:
        """Update connection amount (0-1)."""
        return self.update_connection(source_bus, target_slot, target_param, amount=amount)
    
    def set_offset(self, source_bus: int, target_slot: int, target_param: str, offset: float) -> bool:
        """Update connection offset (-1 to +1)."""
        return self.update_connection(source_bus, target_slot, target_param, offset=offset)
    
    def set_polarity(self, source_bus: int, target_slot: int, target_param: str, polarity: Polarity) -> bool:
        """Update connection polarity."""
        return self.update_connection(source_bus, target_slot, target_param, polarity=polarity)
    
    def set_invert(self, source_bus: int, target_slot: int, target_param: str, invert: bool) -> bool:
        """Update connection invert flag."""
        return self.update_connection(source_bus, target_slot, target_param, invert=invert)
    
    def get_connections_for_bus(self, source_bus: int) -> List[ModConnection]:
        """Get all connections from a specific mod bus."""
        return [c for c in self._connections.values() if c.source_bus == source_bus]
    
    def get_connections_for_target(self, target_slot: int, target_param: Optional[str] = None) -> List[ModConnection]:
        """Get all connections to a specific generator slot (and optionally param)."""
        conns = [c for c in self._connections.values() if c.target_slot == target_slot]
        if target_param:
            conns = [c for c in conns if c.target_param == target_param]
        return conns
    
    def get_all_connections(self) -> List[ModConnection]:
        """Get all connections."""
        return list(self._connections.values())
    
    def clear(self) -> None:
        """Remove all connections."""
        self._connections.clear()
        self.all_cleared.emit()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize all connections for preset saving."""
        return {
            'connections': [c.to_dict() for c in self._connections.values()]
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load connections from preset data.
        
        Clears existing connections first.
        Handles backward compatibility with old format.
        """
        self.clear()
        
        for conn_data in data.get('connections', []):
            try:
                conn = ModConnection.from_dict(conn_data)
                self._connections[conn.key] = conn
                self.connection_added.emit(conn)
            except (KeyError, TypeError, ValueError) as e:
                print(f"Warning: Invalid connection data: {conn_data} ({e})")
    
    def __len__(self) -> int:
        return len(self._connections)
    
    def __contains__(self, key: str) -> bool:
        return key in self._connections
