"""
Boid Modulation Engine - Flocking Simulation for Position-Based Routing

Boids fly over the mod matrix grid and create temporary modulation
connections at their positions. When a boid is over a cell (source row,
target column), it adds depth to that routing.

Key behaviors:
- Configurable number of boids (1-24)
- Classic flocking: separation, alignment, cohesion
- Boundary bounce (not wrap)
- Zone filtering (respects enabled target zones)
- Fading contributions when boid leaves cell
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Callable


# Grid layout per spec (149 columns matches unified bus layout)
GRID_COLS = 149  # 0-148 (matches unified bus targets)
GRID_ROWS = 16   # 0-15 (4 mod slots x 4 outputs)

# Boid limits
MIN_BOID_COUNT = 1
MAX_BOID_COUNT = 24
DEFAULT_BOID_COUNT = 8

# Simulation
SIM_HZ = 20
SIM_DT = 1.0 / SIM_HZ
EPS = 1e-6


class XorShift32:
    """Deterministic PRNG using xorshift32 algorithm."""

    def __init__(self, seed: int):
        self._state = (seed & 0xFFFFFFFF) or 1

    def next_uint32(self) -> int:
        x = self._state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self._state = x
        return x

    def next_float(self) -> float:
        """Random float in [0, 1)."""
        return self.next_uint32() * 2.3283064365386963e-10

    def next_float_range(self, lo: float, hi: float) -> float:
        """Random float in [lo, hi)."""
        return lo + self.next_float() * (hi - lo)


@dataclass
class Boid:
    """Single boid with position and velocity in [0,1) x [0,1) space."""
    x: float = 0.5
    y: float = 0.5
    vx: float = 0.0
    vy: float = 0.0


class BoidEngine:
    """
    Boid flocking simulation for position-based modulation.

    Boids fly over a grid and their positions determine which
    mod matrix cells get temporary modulation contributions.
    """

    def __init__(self):
        self._grid_cols = GRID_COLS
        self._grid_rows = GRID_ROWS

        # Boid list
        self._boids: List[Boid] = []
        self._boid_count = DEFAULT_BOID_COUNT

        # Parameters (normalized 0-1)
        self._dispersion = 0.5
        self._energy = 0.5
        self._fade = 0.5
        self._depth = 1.0

        # Cell contributions: (row, col) -> current value
        self._cell_values: Dict[Tuple[int, int], float] = {}

        # Track which cells each boid occupies
        self._boid_cells: Dict[int, Tuple[int, int]] = {}

        # Cell filter callback (set by controller, checks both row and column)
        self._cell_filter: Optional[Callable[[int, int], bool]] = None

        # RNG
        self._rng: Optional[XorShift32] = None
        self._initialized = False

    def initialize(self, seed: int) -> None:
        """Initialize simulation with given seed."""
        self._rng = XorShift32(seed)
        self._boids = []
        self._cell_values.clear()
        self._boid_cells.clear()

        # Create boids with random positions/velocities
        for _ in range(self._boid_count):
            b = Boid(
                x=self._rng.next_float(),
                y=self._rng.next_float(),
                vx=self._rng.next_float_range(-0.01, 0.01),
                vy=self._rng.next_float_range(-0.01, 0.01),
            )
            self._boids.append(b)

        self._initialized = True

    def set_cell_filter(self, filter_func: Callable[[int, int], bool]) -> None:
        """Set callback to filter cells by row and column."""
        self._cell_filter = filter_func

    def set_boid_count(self, count: int) -> None:
        """Change number of boids."""
        count = max(MIN_BOID_COUNT, min(MAX_BOID_COUNT, count))
        if count == self._boid_count:
            return

        old_count = self._boid_count
        self._boid_count = count

        if not self._initialized:
            return

        if count > old_count:
            # Add new boids
            for _ in range(count - old_count):
                b = Boid(
                    x=self._rng.next_float(),
                    y=self._rng.next_float(),
                    vx=self._rng.next_float_range(-0.01, 0.01),
                    vy=self._rng.next_float_range(-0.01, 0.01),
                )
                self._boids.append(b)
        else:
            # Remove excess boids and clear their cells
            for i in range(count, old_count):
                if i in self._boid_cells:
                    del self._boid_cells[i]
            self._boids = self._boids[:count]

    def set_dispersion(self, value: float) -> None:
        """Set dispersion (0=tight flock, 1=scattered)."""
        self._dispersion = max(0.0, min(1.0, value))

    def set_energy(self, value: float) -> None:
        """Set energy (0=slow drift, 1=fast/chaotic)."""
        self._energy = max(0.0, min(1.0, value))

    def set_fade(self, value: float) -> None:
        """Set fade time (0=fast 0.1s, 1=slow 2s)."""
        self._fade = max(0.0, min(1.0, value))

    def set_depth(self, value: float) -> None:
        """Set connection depth (modulation strength)."""
        self._depth = max(0.0, min(1.0, value))

    def tick(self) -> None:
        """Advance simulation by one tick (call at SIM_HZ)."""
        if not self._initialized:
            return

        # Update flocking physics
        self._update_boids()

        # Update cell contributions
        self._update_cells()

    def _update_boids(self) -> None:
        """Apply flocking rules and update positions."""
        n = len(self._boids)
        if n == 0:
            return

        # Compute derived parameters
        # Dispersion affects separation strength (inverse relationship)
        sep_weight = 1.5 * (1.0 - self._dispersion * 0.8)
        align_weight = 1.0
        cohesion_weight = 0.8 * (1.0 - self._dispersion * 0.5)

        # Energy affects max speed and acceleration
        base_speed = 0.005
        max_speed = base_speed + self._energy * 0.025
        max_force = 0.001 + self._energy * 0.004

        # Neighbor radius
        neighbor_radius = 0.15 + self._dispersion * 0.1

        for i, boid in enumerate(self._boids):
            # Accumulate steering forces
            sep_x, sep_y = 0.0, 0.0
            align_x, align_y = 0.0, 0.0
            coh_x, coh_y = 0.0, 0.0
            neighbor_count = 0

            for j, other in enumerate(self._boids):
                if i == j:
                    continue

                dx = other.x - boid.x
                dy = other.y - boid.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < neighbor_radius and dist > EPS:
                    neighbor_count += 1

                    # Separation: steer away from close neighbors
                    if dist < neighbor_radius * 0.5:
                        sep_x -= dx / dist
                        sep_y -= dy / dist

                    # Alignment: match velocity
                    align_x += other.vx
                    align_y += other.vy

                    # Cohesion: steer toward center
                    coh_x += other.x
                    coh_y += other.y

            # Apply steering
            ax, ay = 0.0, 0.0

            if neighbor_count > 0:
                # Separation
                ax += sep_x * sep_weight
                ay += sep_y * sep_weight

                # Alignment
                align_x /= neighbor_count
                align_y /= neighbor_count
                ax += (align_x - boid.vx) * align_weight
                ay += (align_y - boid.vy) * align_weight

                # Cohesion
                coh_x = coh_x / neighbor_count - boid.x
                coh_y = coh_y / neighbor_count - boid.y
                ax += coh_x * cohesion_weight
                ay += coh_y * cohesion_weight

            # Add slight random jitter based on energy
            jitter = self._energy * 0.002
            ax += self._rng.next_float_range(-jitter, jitter)
            ay += self._rng.next_float_range(-jitter, jitter)

            # Limit acceleration
            a_mag = math.sqrt(ax * ax + ay * ay)
            if a_mag > max_force:
                ax = ax / a_mag * max_force
                ay = ay / a_mag * max_force

            # Update velocity
            boid.vx += ax
            boid.vy += ay

            # Limit speed
            v_mag = math.sqrt(boid.vx * boid.vx + boid.vy * boid.vy)
            if v_mag > max_speed:
                boid.vx = boid.vx / v_mag * max_speed
                boid.vy = boid.vy / v_mag * max_speed

            # Update position
            boid.x += boid.vx
            boid.y += boid.vy

            # Bounce at boundaries
            if boid.x < 0:
                boid.x = -boid.x
                boid.vx = abs(boid.vx)
            elif boid.x >= 1:
                boid.x = 2 - boid.x
                boid.vx = -abs(boid.vx)

            if boid.y < 0:
                boid.y = -boid.y
                boid.vy = abs(boid.vy)
            elif boid.y >= 1:
                boid.y = 2 - boid.y
                boid.vy = -abs(boid.vy)

            # Clamp to valid range
            boid.x = max(0.0, min(0.9999, boid.x))
            boid.y = max(0.0, min(0.9999, boid.y))

    def _update_cells(self) -> None:
        """Update cell contributions based on boid positions."""
        # Fade rate: 0 -> 0.1s decay, 1 -> 2s decay
        fade_time = 0.1 + self._fade * 1.9
        fade_rate = SIM_DT / fade_time

        # Fade all existing values
        to_remove = []
        for cell, value in self._cell_values.items():
            new_val = value - fade_rate
            if new_val <= 0:
                to_remove.append(cell)
            else:
                self._cell_values[cell] = new_val

        for cell in to_remove:
            del self._cell_values[cell]

        # Update cells for current boid positions
        for i, boid in enumerate(self._boids):
            col = int(boid.x * self._grid_cols)
            row = int(boid.y * self._grid_rows)

            # Clamp to grid bounds
            col = max(0, min(self._grid_cols - 1, col))
            row = max(0, min(self._grid_rows - 1, row))

            # Apply cell filter (checks both row and column restrictions)
            if self._cell_filter and not self._cell_filter(row, col):
                # Boid is in disallowed cell, don't contribute
                if i in self._boid_cells:
                    del self._boid_cells[i]
                continue

            cell = (row, col)
            self._boid_cells[i] = cell

            # Set cell to full depth (will fade when boid leaves)
            self._cell_values[cell] = self._depth

    def get_contributions(self) -> List[Tuple[int, int, float]]:
        """
        Get current cell contributions for OSC sending.

        Returns:
            List of (row, col, offset) tuples
        """
        return [(row, col, val) for (row, col), val in self._cell_values.items()]

    def get_positions(self) -> List[Tuple[float, float]]:
        """Get current boid positions for visualization."""
        return [(b.x, b.y) for b in self._boids]

    def get_cell_values(self) -> Dict[Tuple[int, int], float]:
        """Get cell values for visualization."""
        return self._cell_values.copy()

    @property
    def boid_count(self) -> int:
        return self._boid_count

    @property
    def initialized(self) -> bool:
        return self._initialized

    def reset(self) -> None:
        """Reset simulation state."""
        self._boids.clear()
        self._cell_values.clear()
        self._boid_cells.clear()
        self._initialized = False
