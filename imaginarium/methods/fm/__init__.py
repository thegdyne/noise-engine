"""
imaginarium/methods/fm/__init__.py
FM/AM/PM synthesis methods
"""

from .simple_fm import SimpleFMTemplate
from .feedback_fm import FeedbackFMTemplate
from .ratio_stack import RatioStackTemplate
from .ring_mod import RingModTemplate
from .hard_sync import HardSyncTemplate
from .phase_mod import PhaseModTemplate
from .am_chorus import AMChorusTemplate

__all__ = [
    "SimpleFMTemplate",
    "FeedbackFMTemplate",
    "RatioStackTemplate",
    "RingModTemplate",
    "HardSyncTemplate",
    "PhaseModTemplate",
    "AMChorusTemplate",
]

# Method registry for this family
FM_METHODS = {
    "fm/simple_fm": SimpleFMTemplate,
    "fm/feedback_fm": FeedbackFMTemplate,
    "fm/ratio_stack": RatioStackTemplate,
    "fm/ring_mod": RingModTemplate,
    "fm/hard_sync": HardSyncTemplate,
    "fm/phase_mod": PhaseModTemplate,
    "fm/am_chorus": AMChorusTemplate,
}
