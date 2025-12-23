"""
imaginarium/methods/spectral/__init__.py
Spectral synthesis methods - FFT, additive
"""

from .additive import AdditiveTemplate
from .spectral_drone import SpectralDroneTemplate

__all__ = [
    "AdditiveTemplate",
    "SpectralDroneTemplate",
]

# Method registry for this family
SPECTRAL_METHODS = {
    "spectral/additive": AdditiveTemplate,
    "spectral/spectral_drone": SpectralDroneTemplate,
}
