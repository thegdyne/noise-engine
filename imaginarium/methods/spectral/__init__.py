"""
imaginarium/methods/spectral/__init__.py
Spectral synthesis methods - FFT, additive, wavetable
"""

from .additive import AdditiveTemplate
from .spectral_drone import SpectralDroneTemplate
from .wavetable import WavetableTemplate
from .vocoder import VocoderTemplate
from .harmonic_series import HarmonicSeriesTemplate

__all__ = [
    "AdditiveTemplate",
    "SpectralDroneTemplate",
    "WavetableTemplate",
    "VocoderTemplate",
    "HarmonicSeriesTemplate",
]

# Method registry for this family
SPECTRAL_METHODS = {
    "spectral/additive": AdditiveTemplate,
    "spectral/spectral_drone": SpectralDroneTemplate,
    "spectral/wavetable": WavetableTemplate,
    "spectral/vocoder": VocoderTemplate,
    "spectral/harmonic_series": HarmonicSeriesTemplate,
}
