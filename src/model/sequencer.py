"""
Sequencer Data Models — SH-101 Style Step Sequencer

Data models for the step sequencer subsystem:
- StepType: NOTE / REST / TIE
- SeqStep: Single step with type, note, velocity
- SeqSettings: Sequencer configuration (rate, length, play mode, steps)
- MotionMode: OFF / ARP / SEQ mode selector
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List


class StepType(Enum):
    """Step type for sequencer steps."""
    NOTE = auto()
    REST = auto()
    TIE = auto()


class MotionMode(Enum):
    """Motion mode for slot: OFF, ARP, or SEQ."""
    OFF = 0
    ARP = 1
    SEQ = 2


class PlayMode(Enum):
    """Sequencer play direction."""
    FORWARD = auto()
    REVERSE = auto()
    PINGPONG = auto()
    RANDOM = auto()


@dataclass
class SeqStep:
    """Single step in the sequence."""
    step_type: StepType = StepType.REST
    note: int = 60      # MIDI note number (0-127)
    velocity: int = 100  # MIDI velocity (1-127)


@dataclass
class SeqSettings:
    """Sequencer configuration."""
    rate: float = 0.25          # Beats per step (0.25 = 16th notes)
    length: int = 16            # Number of active steps (1-16)
    play_mode: PlayMode = PlayMode.FORWARD
    steps: List[SeqStep] = field(
        default_factory=lambda: [SeqStep() for _ in range(16)]
    )
