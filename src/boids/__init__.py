"""
Boid Modulation System

Position-based modulation routing using flocking simulation.
Boids fly over the mod matrix grid and create temporary connections.
"""

from .boid_state import BoidState, generate_random_seed
from .boid_engine import BoidEngine
from .boid_controller import BoidController

__all__ = [
    'BoidState',
    'BoidEngine',
    'BoidController',
    'generate_random_seed',
]
