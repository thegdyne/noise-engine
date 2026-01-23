"""
Mod Routing State
Data model for modulation connections between mod buses and generator/extended parameters.

Each connection routes a mod bus output to a target with:
- amount: modulation range width (0-1)
- offset: shifts mod range up/down (-1 to +1)
- polarity: bipolar/uni+/uni-
- invert: flip mod signal before polarity

Supports two routing systems:
- Generator routes: target_slot (1-8) + target_param ("cutoff", etc.)
- Extended routes: target_str ("mod:1:rate", "fx:heat:drive", "send:3:ec")
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal


# ============================================================================
# EXTENDED_PARAMS: Canonical definition of all extended modulation targets
# Wire key format: "type:index:param"
# ============================================================================

# Modulator params: mod:1..4:p1..p4 (16 entries)
MOD_PARAMS = [
    (f"mod:{slot}:{param}", f"M{slot} P{param[-1]}")
    for slot in range(1, 5)
    for param in ['p1', 'p2', 'p3', 'p4']
]

# Channel params: sends + pan (24 entries)
CHAN_PARAMS = [
    (f"send:{ch}:ec", f"CH{ch} Echo") for ch in range(1, 9)
] + [
    (f"send:{ch}:vb", f"CH{ch} Verb") for ch in range(1, 9)
] + [
    (f"chan:{ch}:pan", f"CH{ch} Pan") for ch in range(1, 9)
]

# All extended params: 16 mod + 24 chan = 40 total
EXTENDED_PARAMS: List[Tuple[str, str]] = MOD_PARAMS + CHAN_PARAMS

# Set of valid extended target wire keys for validation
VALID_EXT_TARGETS: Set[str] = {wire_key for wire_key, _ in EXTENDED_PARAMS}


# ============================================================================
# DEFAULT_ROUTE_PARAMS: Shared defaults for all new routes (Invariant #6)
# ============================================================================
DEFAULT_ROUTE_PARAMS = {
    'depth': 1.0,
    'amount': 0.5,
    'offset': 0.0,
    'polarity': 0,  # BIPOLAR
    'invert': False,
}


def make_default_route_params() -> Dict[str, Any]:
    """Factory function for route defaults (alternative to constant)."""
    return dict(DEFAULT_ROUTE_PARAMS)


def create_default_connection(source_bus: int, *,
                               target_slot: Optional[int] = None,
                               target_param: Optional[str] = None,
                               target_str: Optional[str] = None) -> 'ModConnection':
    """
    Create a new ModConnection with default parameters (Invariant #6).

    Use this factory function instead of creating ModConnection directly
    to ensure consistent defaults across all route creation paths.
    """
    params = make_default_route_params()
    return ModConnection(
        source_bus=source_bus,
        target_slot=target_slot,
        target_param=target_param,
        target_str=target_str,
        depth=params['depth'],
        amount=params['amount'],
        offset=params['offset'],
        polarity=Polarity(params['polarity']),
        invert=params['invert'],
    )


def is_valid_ext_target(target_str: str) -> bool:
    """Check if target_str is a valid extended target wire key."""
    return target_str in VALID_EXT_TARGETS


class Polarity(Enum):
    """Modulation polarity modes."""
    BIPOLAR = 0   # Sweeps both above and below center
    UNI_POS = 1   # Only sweeps above center (positive)
    UNI_NEG = 2   # Only sweeps below center (negative)


# Target string builders
def build_mod_target(slot: int, param: str) -> str:
    """Build modulator target string: mod:{slot}:{param}"""
    return f"mod:{slot}:{param}"


def build_fx_target(fx_type: str, param: str) -> str:
    """Build FX target string: fx:{type}:{param}"""
    return f"fx:{fx_type}:{param}"


def build_send_target(slot: int, send_type: str) -> str:
    """Build send target string: send:{slot}:{send}"""
    return f"send:{slot}:{send_type}"


@dataclass
class ModConnection:
    """
    A single modulation routing connection.

    Default values are derived from DEFAULT_ROUTE_PARAMS (Invariant #6).
    """
    source_bus: int       # 0-15 (4 slots × 4 outputs)

    # Generator targets (existing)
    target_slot: Optional[int] = None      # 1-8 (generator slot)
    target_param: Optional[str] = None     # 'cutoff', 'frequency', 'resonance', etc.

    # Extended targets (new)
    target_str: Optional[str] = None       # 'mod:1:p1', 'send:3:ec', 'chan:1:pan'

    # Connection parameters (defaults match DEFAULT_ROUTE_PARAMS)
    depth: float = 1.0    # Always 1.0 (kept for SC compat, not user-facing)
    amount: float = 0.5   # 0.0 to 1.0 (modulation range)
    offset: float = 0.0   # -1.0 to 1.0 (shifts mod range up/down)
    polarity: Polarity = Polarity.BIPOLAR  # Polarity(0)
    invert: bool = False  # Flip signal before polarity
    
    @property
    def is_extended(self) -> bool:
        """True if this is an extended route (FX/mod/send)."""
        return self.target_str is not None
    
    @property
    def key(self) -> str:
        """Unique key for this connection."""
        if self.is_extended:
            return f"{self.source_bus}_{self.target_str}"
        else:
            return f"{self.source_bus}_{self.target_slot}_{self.target_param}"
    
    @property
    def effective_range(self) -> float:
        """Depth × Amount = actual modulation range."""
        return self.depth * self.amount
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for preset saving."""
        data = {
            'source_bus': self.source_bus,
            'depth': self.depth,
            'amount': self.amount,
            'offset': self.offset,
            'polarity': self.polarity.value,
            'invert': self.invert,
        }
        
        # Add type-specific fields
        if self.is_extended:
            data['target_str'] = self.target_str
        else:
            data['target_slot'] = self.target_slot
            data['target_param'] = self.target_param
        
        return data
    
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
        
        # Determine connection type
        if 'target_str' in data:
            # Extended route
            return cls(
                source_bus=data['source_bus'],
                target_str=data['target_str'],
                depth=depth,
                amount=data.get('amount', 1.0),
                offset=data.get('offset', 0.0),
                polarity=Polarity(data.get('polarity', 0)),
                invert=invert,
            )
        else:
            # Generator route (backward compatible)
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
    
    Supports both generator routes (existing) and extended routes (new).
    Emits signals when connections change so UI and OSC can react.
    """
    
    # Signals
    connection_added = pyqtSignal(object)      # ModConnection
    connection_removed = pyqtSignal(object)    # ModConnection (changed signature to pass whole connection)
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
    
    def remove_connection(self, source_bus: int, target_slot: Optional[int] = None, 
                         target_param: Optional[str] = None, target_str: Optional[str] = None) -> bool:
        """
        Remove a connection.
        
        For generator routes: provide source_bus, target_slot, target_param
        For extended routes: provide source_bus, target_str
        
        Returns True if removed, False if not found.
        """
        # Build key based on what was provided
        if target_str is not None:
            key = f"{source_bus}_{target_str}"
        else:
            key = f"{source_bus}_{target_slot}_{target_param}"
        
        conn = self._connections.pop(key, None)
        if conn is None:
            return False
        
        self.connection_removed.emit(conn)
        return True
    
    def get_connection(self, source_bus: int, target_slot: Optional[int] = None,
                      target_param: Optional[str] = None, target_str: Optional[str] = None) -> Optional[ModConnection]:
        """
        Get a specific connection.
        
        For generator routes: provide source_bus, target_slot, target_param
        For extended routes: provide source_bus, target_str
        """
        if target_str is not None:
            key = f"{source_bus}_{target_str}"
        else:
            key = f"{source_bus}_{target_slot}_{target_param}"
        
        return self._connections.get(key)
    
    def update_connection(self, source_bus: int,
                          target_slot: Optional[int] = None,
                          target_param: Optional[str] = None,
                          target_str: Optional[str] = None,
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
        conn = self.get_connection(source_bus, target_slot, target_param, target_str)
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
    
    def set_depth(self, source_bus: int, target_slot: Optional[int] = None, 
                 target_param: Optional[str] = None, target_str: Optional[str] = None,
                 depth: float = 1.0) -> bool:
        """Update connection depth (0-1)."""
        return self.update_connection(source_bus, target_slot, target_param, target_str, depth=depth)
    
    def set_amount(self, source_bus: int, target_slot: Optional[int] = None,
                  target_param: Optional[str] = None, target_str: Optional[str] = None,
                  amount: float = 0.5) -> bool:
        """Update connection amount (0-1)."""
        return self.update_connection(source_bus, target_slot, target_param, target_str, amount=amount)
    
    def set_offset(self, source_bus: int, target_slot: Optional[int] = None,
                  target_param: Optional[str] = None, target_str: Optional[str] = None,
                  offset: float = 0.0) -> bool:
        """Update connection offset (-1 to +1)."""
        return self.update_connection(source_bus, target_slot, target_param, target_str, offset=offset)
    
    def set_polarity(self, source_bus: int, target_slot: Optional[int] = None,
                    target_param: Optional[str] = None, target_str: Optional[str] = None,
                    polarity: Polarity = Polarity.BIPOLAR) -> bool:
        """Update connection polarity."""
        return self.update_connection(source_bus, target_slot, target_param, target_str, polarity=polarity)
    
    def set_invert(self, source_bus: int, target_slot: Optional[int] = None,
                  target_param: Optional[str] = None, target_str: Optional[str] = None,
                  invert: bool = False) -> bool:
        """Update connection invert flag."""
        return self.update_connection(source_bus, target_slot, target_param, target_str, invert=invert)
    
    def get_connections_for_bus(self, source_bus: int) -> List[ModConnection]:
        """Get all connections from a specific mod bus."""
        return [c for c in self._connections.values() if c.source_bus == source_bus]
    
    def get_connections_for_target(self, target_slot: Optional[int] = None, 
                                   target_param: Optional[str] = None) -> List[ModConnection]:
        """Get all connections to a specific generator slot (and optionally param)."""
        if target_slot is None:
            return []
        conns = [c for c in self._connections.values() 
                if not c.is_extended and c.target_slot == target_slot]
        if target_param:
            conns = [c for c in conns if c.target_param == target_param]
        return conns
    
    def get_generator_connections(self) -> List[ModConnection]:
        """Get all generator (non-extended) connections."""
        return [c for c in self._connections.values() if not c.is_extended]
    
    def get_extended_connections(self) -> List[ModConnection]:
        """Get all extended (FX/mod/send) connections."""
        return [c for c in self._connections.values() if c.is_extended]
    
    def get_all_connections(self) -> List[ModConnection]:
        """Get all connections."""
        return list(self._connections.values())

    def clear(self) -> None:
        """Remove all connections."""
        # Remove each connection individually to trigger OSC messages
        keys = list(self._connections.keys())
        for key in keys:
            conn = self._connections[key]
            del self._connections[key]
            self.connection_removed.emit(conn)
        self.all_cleared.emit()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize all connections for preset saving.

        Per spec: Generator routes in 'connections', extended in 'ext_mod_routes'.
        """
        gen_conns = [c.to_dict() for c in self._connections.values() if not c.is_extended]
        ext_conns = [c.to_dict() for c in self._connections.values() if c.is_extended]

        return {
            'connections': gen_conns,           # Generator routes (backward compat)
            'ext_mod_routes': ext_conns,        # Extended routes (per spec)
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load connections from preset data with exact replacement semantics.

        Per spec (5.2 Load):
        1. Parse preset into desired route sets (validate, deduplicate)
        2. Clear local state
        3. Add all desired routes
        4. Emit signals for each (OSC projection happens via signal handlers)

        Backward compatibility:
        - Accepts both 'ext_mod_routes' (new) and 'ext_connections' (legacy)
        - Missing ext field treated as [] (Invariant #11)
        - Duplicates: later entry overwrites earlier (Invariant #12)
        """
        # ----------------------------------------------------------------
        # 1. Parse preset into desired route sets
        # ----------------------------------------------------------------
        desired_gen_conns: Dict[str, ModConnection] = {}  # key -> conn
        desired_ext_conns: Dict[str, ModConnection] = {}  # key -> conn

        # Generator connections
        for conn_data in data.get('connections', []):
            try:
                conn = ModConnection.from_dict(conn_data)
                if not conn.is_extended:
                    # Later entries overwrite earlier (Invariant #12)
                    desired_gen_conns[conn.key] = conn
            except (KeyError, TypeError, ValueError) as e:
                print(f"Warning: Invalid generator connection data: {conn_data} ({e})")

        # Extended connections - try new key first, then legacy
        ext_data = data.get('ext_mod_routes', data.get('ext_connections', []))
        for conn_data in ext_data:
            try:
                conn = ModConnection.from_dict(conn_data)
                if conn.is_extended:
                    # Validate extended target (Error Handling #1)
                    target_str = conn.target_str
                    if not is_valid_ext_target(target_str):
                        print(f"Warning: Invalid extended target '{target_str}', skipping")
                        continue
                    # Later entries overwrite earlier (Invariant #12)
                    desired_ext_conns[conn.key] = conn
            except (KeyError, TypeError, ValueError) as e:
                print(f"Warning: Invalid extended connection data: {conn_data} ({e})")

        # ----------------------------------------------------------------
        # 2. Clear local state (don't emit individual remove signals)
        # ----------------------------------------------------------------
        self._connections.clear()

        # ----------------------------------------------------------------
        # 3. Add all desired routes
        # ----------------------------------------------------------------
        for conn in desired_gen_conns.values():
            self._connections[conn.key] = conn
            self.connection_added.emit(conn)

        for conn in desired_ext_conns.values():
            self._connections[conn.key] = conn
            self.connection_added.emit(conn)

        # Signal that all routes were cleared and replaced
        self.all_cleared.emit()
    
    def load_from_preset(self, data: Dict[str, Any]) -> Tuple[
        List['ModConnection'],  # removed_gen: generator routes to remove from SC
        List['ModConnection'],  # removed_ext: extended routes to remove from SC
        List['ModConnection'],  # added_gen: generator routes to add/upsert in SC
        List['ModConnection'],  # added_ext: extended routes to add/upsert in SC
    ]:
        """
        Load connections from preset with exact replacement semantics.

        Per spec (5.2 Load - exact replacement):
        1. Parse preset into desired route sets (validate, deduplicate)
        2. Snapshot current state
        3. Compute removal sets (key-disjoint from desired)
        4. Replace local state
        5. Return deltas for OSC projection

        Returns tuple of (removed_gen, removed_ext, added_gen, added_ext)
        for the controller to project to the backend.
        """
        # ----------------------------------------------------------------
        # 1. Parse preset into desired route sets
        # ----------------------------------------------------------------
        desired_gen: Dict[str, ModConnection] = {}  # key -> conn
        desired_ext: Dict[str, ModConnection] = {}  # key -> conn

        # Generator connections
        for conn_data in data.get('connections', []):
            try:
                conn = ModConnection.from_dict(conn_data)
                if not conn.is_extended:
                    desired_gen[conn.key] = conn  # Later overwrites earlier
            except (KeyError, TypeError, ValueError) as e:
                print(f"Warning: Invalid generator connection data: {conn_data} ({e})")

        # Extended connections - try new key first, then legacy
        ext_data = data.get('ext_mod_routes', data.get('ext_connections', []))
        for conn_data in ext_data:
            try:
                conn = ModConnection.from_dict(conn_data)
                if conn.is_extended:
                    # Validate extended target
                    if conn.target_str and not is_valid_ext_target(conn.target_str):
                        print(f"Warning: Invalid extended target '{conn.target_str}', skipping")
                        continue
                    desired_ext[conn.key] = conn  # Later overwrites earlier
            except (KeyError, TypeError, ValueError) as e:
                print(f"Warning: Invalid extended connection data: {conn_data} ({e})")

        # ----------------------------------------------------------------
        # 2. Snapshot current state
        # ----------------------------------------------------------------
        current_gen_keys = {k for k, c in self._connections.items() if not c.is_extended}
        current_ext_keys = {k for k, c in self._connections.items() if c.is_extended}

        # ----------------------------------------------------------------
        # 3. Compute removal sets (key-disjoint from desired by construction)
        # ----------------------------------------------------------------
        remove_gen_keys = current_gen_keys - set(desired_gen.keys())
        remove_ext_keys = current_ext_keys - set(desired_ext.keys())

        removed_gen = [self._connections[k] for k in remove_gen_keys]
        removed_ext = [self._connections[k] for k in remove_ext_keys]

        # ----------------------------------------------------------------
        # 4. Replace local state (clear then add)
        # ----------------------------------------------------------------
        self._connections.clear()

        for conn in desired_gen.values():
            self._connections[conn.key] = conn

        for conn in desired_ext.values():
            self._connections[conn.key] = conn

        # ----------------------------------------------------------------
        # 5. Return deltas for OSC projection
        # ----------------------------------------------------------------
        return (
            removed_gen,
            removed_ext,
            list(desired_gen.values()),
            list(desired_ext.values()),
        )

    def get_all_keys(self) -> Tuple[Set[str], Set[str]]:
        """Return (generator_keys, extended_keys) for current connections."""
        gen_keys = {k for k, c in self._connections.items() if not c.is_extended}
        ext_keys = {k for k, c in self._connections.items() if c.is_extended}
        return gen_keys, ext_keys

    def __len__(self) -> int:
        return len(self._connections)

    def __contains__(self, key: str) -> bool:
        return key in self._connections
