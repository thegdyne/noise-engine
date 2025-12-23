"""
imaginarium/methods/texture/__init__.py
Texture synthesis methods - granular, stochastic, noise-based
"""

from .granular_cloud import GranularCloudTemplate
from .dust_resonator import DustResonatorTemplate
from .noise_drone import NoiseDroneTemplate
from .chaos_osc import ChaosOscTemplate
from .bitcrush import BitcrushTemplate
from .noise_rhythm import NoiseRhythmTemplate

__all__ = [
    "GranularCloudTemplate",
    "DustResonatorTemplate",
    "NoiseDroneTemplate",
    "ChaosOscTemplate",
    "BitcrushTemplate",
    "NoiseRhythmTemplate",
]

# Method registry for this family
TEXTURE_METHODS = {
    "texture/granular_cloud": GranularCloudTemplate,
    "texture/dust_resonator": DustResonatorTemplate,
    "texture/noise_drone": NoiseDroneTemplate,
    "texture/chaos_osc": ChaosOscTemplate,
    "texture/bitcrush": BitcrushTemplate,
    "texture/noise_rhythm": NoiseRhythmTemplate,
}
