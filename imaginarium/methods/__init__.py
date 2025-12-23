"""
imaginarium/methods/__init__.py
Method registry - discovers and loads synthesis templates
"""

from typing import Dict, List, Optional
from .base import MethodTemplate, MethodDefinition

# Global registry
_REGISTRY: Dict[str, MethodTemplate] = {}


def register_method(template: MethodTemplate) -> None:
    """Register a method template."""
    method_id = template.definition.method_id
    if method_id in _REGISTRY:
        raise ValueError(f"Method {method_id} already registered")
    _REGISTRY[method_id] = template


def get_method(method_id: str) -> Optional[MethodTemplate]:
    """Get a registered method by ID."""
    return _REGISTRY.get(method_id)


def list_methods() -> List[str]:
    """List all registered method IDs."""
    return list(_REGISTRY.keys())


def list_methods_by_family(family: str) -> List[str]:
    """List method IDs for a specific family."""
    return [
        mid for mid, template in _REGISTRY.items()
        if template.definition.family == family
    ]


def get_all_methods() -> Dict[str, MethodTemplate]:
    """Get all registered methods."""
    return dict(_REGISTRY)


# =============================================================================
# Auto-registration of built-in methods
# =============================================================================

def _register_builtins():
    """Register all built-in method templates."""
    # Import here to avoid circular imports
    from .subtractive.bright_saw import BrightSawTemplate
    from .subtractive.dark_pulse import DarkPulseTemplate
    from .subtractive.noise_filtered import NoiseFilteredTemplate
    from .subtractive.supersaw import SupersawTemplate
    from .fm.simple_fm import SimpleFMTemplate
    from .fm.feedback_fm import FeedbackFMTemplate
    from .fm.ratio_stack import RatioStackTemplate
    from .fm.ring_mod import RingModTemplate
    from .fm.hard_sync import HardSyncTemplate
    from .physical.karplus import KarplusTemplate
    from .physical.modal import ModalTemplate
    from .physical.bowed import BowedTemplate
    from .physical.formant import FormantTemplate
    from .spectral.additive import AdditiveTemplate
    from .texture.granular_cloud import GranularCloudTemplate
    from .texture.dust_resonator import DustResonatorTemplate
    from .texture.noise_drone import NoiseDroneTemplate
    from .subtractive.wavefold import WavefoldTemplate
    from .fm.phase_mod import PhaseModTemplate
    from .fm.am_chorus import AMChorusTemplate
    from .physical.membrane import MembraneTemplate
    from .physical.tube import TubeTemplate
    from .spectral.spectral_drone import SpectralDroneTemplate
    from .texture.chaos_osc import ChaosOscTemplate
    from .spectral.wavetable import WavetableTemplate
    from .spectral.vocoder import VocoderTemplate
    from .spectral.harmonic_series import HarmonicSeriesTemplate
    from .physical.comb_resonator import CombResonatorTemplate
    from .texture.bitcrush import BitcrushTemplate
    from .texture.noise_rhythm import NoiseRhythmTemplate

    register_method(BrightSawTemplate())
    register_method(DarkPulseTemplate())
    register_method(NoiseFilteredTemplate())
    register_method(SupersawTemplate())
    register_method(SimpleFMTemplate())
    register_method(FeedbackFMTemplate())
    register_method(RatioStackTemplate())
    register_method(RingModTemplate())
    register_method(HardSyncTemplate())
    register_method(KarplusTemplate())
    register_method(ModalTemplate())
    register_method(BowedTemplate())
    register_method(FormantTemplate())
    register_method(AdditiveTemplate())
    register_method(GranularCloudTemplate())
    register_method(DustResonatorTemplate())
    register_method(NoiseDroneTemplate())
    register_method(WavefoldTemplate())
    register_method(PhaseModTemplate())
    register_method(AMChorusTemplate())
    register_method(MembraneTemplate())
    register_method(TubeTemplate())
    register_method(SpectralDroneTemplate())
    register_method(ChaosOscTemplate())
    register_method(WavetableTemplate())
    register_method(VocoderTemplate())
    register_method(HarmonicSeriesTemplate())
    register_method(CombResonatorTemplate())
    register_method(BitcrushTemplate())
    register_method(NoiseRhythmTemplate())

# Register on import
_register_builtins()
