"""
imaginarium/methods/texture/__init__.py
Texture synthesis methods - granular, stochastic, noise-based
"""

from .granular_cloud import GranularCloudTemplate
from .dust_resonator import DustResonatorTemplate
from .noise_drone import NoiseDroneTemplate

__all__ = [
    "GranularCloudTemplate",
    "DustResonatorTemplate",
    "NoiseDroneTemplate",
]

# Method registry for this family
TEXTURE_METHODS = {
    "texture/granular_cloud": GranularCloudTemplate,
    "texture/dust_resonator": DustResonatorTemplate,
    "texture/noise_drone": NoiseDroneTemplate,
}
