"""
Crossmod OSC Bridge
Syncs CrossmodRoutingState <-> SuperCollider via OSC.

OSC Endpoints:
  /noise/crossmod/route [source, target, param, depth, amount, offset, polarity, invert]
  /noise/crossmod/unroute [source, target, param]
  /noise/crossmod/enabled [source, 0_or_1]
  /noise/crossmod/clear []
"""

from .crossmod_routing_state import CrossmodRoutingState, CrossmodConnection


class CrossmodOSCBridge:
    """Syncs CrossmodRoutingState <-> SuperCollider via OSC."""
    
    # v1 fixed defaults
    DEPTH = 1.0
    POLARITY = 0  # bipolar
    
    def __init__(self, state: CrossmodRoutingState, osc_client):
        """
        Initialize the OSC bridge.
        
        Args:
            state: CrossmodRoutingState to sync
            osc_client: OSC client with send(address, args) method
        """
        self.state = state
        self.osc = osc_client
        self._connect_signals()
    
    def _connect_signals(self):
        """Connect to state signals for automatic OSC sync."""
        self.state.connection_added.connect(self._on_connection_added)
        self.state.connection_removed.connect(self._on_connection_removed)
        self.state.connection_changed.connect(self._on_connection_changed)
        self.state.follower_changed.connect(self._on_follower_changed)
        self.state.all_cleared.connect(self._on_all_cleared)
    
    def _on_connection_added(self, conn: CrossmodConnection):
        """Send route message when connection added."""
        self._send_route(conn)
    
    def _on_connection_changed(self, conn: CrossmodConnection):
        """Send route message when connection parameters change."""
        self._send_route(conn)
    
    def _on_connection_removed(self, source_gen: int, target_gen: int, target_param: str):
        """Send unroute message when connection removed."""
        self.osc.send("/noise/crossmod/unroute", [source_gen, target_gen, target_param])
    
    def _on_follower_changed(self, source_gen: int):
        """Send enabled message when follower state changes."""
        follower = self.state.followers[source_gen]
        enabled_int = 1 if follower.enabled else 0
        self.osc.send("/noise/crossmod/enabled", [source_gen, enabled_int])
    
    def _on_all_cleared(self):
        """Send clear message when all connections cleared."""
        self.osc.send("/noise/crossmod/clear", [])
    
    def _send_route(self, conn: CrossmodConnection):
        """Send route message for a connection."""
        invert_int = 1 if conn.invert else 0
        self.osc.send("/noise/crossmod/route", [
            conn.source_gen,
            conn.target_gen,
            conn.target_param,
            self.DEPTH,
            conn.amount,
            conn.offset,
            self.POLARITY,
            invert_int
        ])
    
    # === Manual sync methods ===
    
    def sync_all_connections(self):
        """Send all current connections to SC (for reconnection)."""
        for conn in self.state.get_all_connections():
            self._send_route(conn)
    
    def sync_all_followers(self):
        """Send all follower states to SC."""
        for source_gen in range(1, 9):
            self._on_follower_changed(source_gen)
    
    def sync_all(self):
        """Full sync of all state to SC."""
        self.sync_all_followers()
        self.sync_all_connections()
