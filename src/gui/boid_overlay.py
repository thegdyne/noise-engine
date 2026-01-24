"""
Boid Visualization Overlay
Draws boids flying around on top of the mod matrix.
"""

from typing import List, Tuple, Optional
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush

from .theme import COLORS


class BoidOverlay(QWidget):
    """
    Transparent overlay widget that draws boids over the mod matrix.

    The boids fly around the grid area, providing visual feedback
    of the boid modulation state.
    """

    # Boid visual settings
    BOID_RADIUS = 6
    TRAIL_LENGTH = 8
    BOID_COLOR = QColor('#cc66ff')  # Purple
    TRAIL_COLOR = QColor('#cc66ff')

    # Maximum boids
    MAX_BOIDS = 24

    def __init__(self, parent=None):
        super().__init__(parent)

        # Make transparent and pass through mouse events
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        # Boid positions: list of (x, y) in [0, 1) space
        self._boid_positions: List[Tuple[float, float]] = []

        # Trail history: list of lists of (x, y) positions
        self._trails: List[List[Tuple[float, float]]] = [[] for _ in range(self.MAX_BOIDS)]

        # Cell contributions for glow effect
        self._cell_contributions: dict = {}

        # Update timer (~30fps)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        self._timer.setInterval(33)

        # Reference to boid controller (set externally)
        self._boid_controller = None

        # Visibility state
        self._visible = True

    def set_boid_controller(self, controller) -> None:
        """Set reference to boid controller for position updates."""
        self._boid_controller = controller

        # Connect to controller signals
        if controller:
            controller.positions_updated.connect(self._on_positions_updated)
            controller.cells_updated.connect(self._on_cells_updated)

    def _on_positions_updated(self, positions: list) -> None:
        """Handle position updates from controller."""
        self._update_trails(positions)
        self._boid_positions = positions
        self.update()

    def _on_cells_updated(self, cells: dict) -> None:
        """Handle cell contribution updates from controller."""
        self._cell_contributions = cells

    def _update_trails(self, new_positions: list) -> None:
        """Update trail history with new positions."""
        num_boids = len(new_positions)

        for i, pos in enumerate(new_positions):
            if i < len(self._trails):
                self._trails[i].append(pos)
                # Limit trail length
                if len(self._trails[i]) > self.TRAIL_LENGTH:
                    self._trails[i].pop(0)

        # Clear trails for inactive boids
        for i in range(num_boids, self.MAX_BOIDS):
            if i < len(self._trails):
                self._trails[i].clear()

    def start(self) -> None:
        """Start the visualization."""
        self._timer.start()
        self.show()

    def stop(self) -> None:
        """Stop the visualization."""
        self._timer.stop()
        self._trails = [[] for _ in range(self.MAX_BOIDS)]
        self._cell_contributions.clear()
        self._boid_positions.clear()
        self.update()

    def set_visible(self, visible: bool) -> None:
        """Toggle visibility."""
        self._visible = visible
        if visible:
            self.show()
        else:
            self.hide()

    def _on_timer(self) -> None:
        """Periodic update (for smooth animation)."""
        if not self._visible:
            return
        self.update()

    def paintEvent(self, event):
        """Draw the boids and trails."""
        if not self._visible or not self._boid_positions:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # Draw cell contributions as background glow
        for (row, col), value in self._cell_contributions.items():
            # Map cell to pixel position
            # Grid is 151 cols x 16 rows
            cx = (col / 151.0) * w
            cy = (row / 16.0) * h
            cell_w = w / 151.0
            cell_h = h / 16.0

            alpha = int(value * 40)
            glow_color = QColor(self.TRAIL_COLOR)
            glow_color.setAlpha(alpha)
            painter.fillRect(
                int(cx), int(cy),
                int(cell_w) + 1, int(cell_h) + 1,
                glow_color
            )

        # Draw trails first (behind boids)
        for i, trail in enumerate(self._trails):
            if len(trail) < 2:
                continue

            for j in range(len(trail) - 1):
                # Fade older trail points
                alpha = int(80 * (j + 1) / len(trail))
                trail_color = QColor(self.TRAIL_COLOR)
                trail_color.setAlpha(alpha)

                # Convert to widget coordinates
                x1 = trail[j][0] * w
                y1 = trail[j][1] * h
                x2 = trail[j + 1][0] * w
                y2 = trail[j + 1][1] * h

                pen = QPen(trail_color, 2)
                painter.setPen(pen)
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Draw boids
        for i, (x, y) in enumerate(self._boid_positions):
            # Convert [0,1) to widget coordinates
            px = x * w
            py = y * h

            # Draw glow/halo
            glow_color = QColor(self.BOID_COLOR)
            glow_color.setAlpha(60)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(
                QPointF(px, py),
                self.BOID_RADIUS * 2,
                self.BOID_RADIUS * 2
            )

            # Draw boid body
            painter.setBrush(QBrush(self.BOID_COLOR))
            painter.drawEllipse(
                QPointF(px, py),
                self.BOID_RADIUS,
                self.BOID_RADIUS
            )

            # Draw bright center
            center_color = QColor('#ffffff')
            center_color.setAlpha(180)
            painter.setBrush(QBrush(center_color))
            painter.drawEllipse(
                QPointF(px, py),
                self.BOID_RADIUS // 3,
                self.BOID_RADIUS // 3
            )

    def resizeEvent(self, event):
        """Handle resize to match parent."""
        super().resizeEvent(event)
        self.update()
