"""
imaginarium/methods/subtractive/noise_filtered.py
Filtered noise synthesis with multiple noise types

Character: Textures, wind, breath, static, percussion, ambience
Uses different noise sources filtered and shaped
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class NoiseFilteredTemplate(MethodTemplate):
    """Filtered noise synthesis with multiple noise types."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="subtractive/noise_filtered",
            family="subtractive",
            display_name="Filtered Noise",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="noise_type",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="linear",
                ),
                ParamAxis(
                    name="cutoff_hz",
                    min_val=100.0,
                    max_val=8000.0,
                    default=1500.0,
                    curve="exp",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.0,
                    max_val=0.95,
                    default=0.3,
                    curve="linear",
                ),
                ParamAxis(
                    name="dust_density",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.0,
                    curve="linear",
                ),
                ParamAxis(
                    name="crackle_amt",
                    min_val=0.0,
                    max_val=0.5,
                    default=0.0,
                    curve="linear",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="darkness",
                    param_weights={
                        "noise_type": 0.6,  # Toward brown
                        "cutoff_hz": -0.8,
                    },
                ),
                MacroControl(
                    name="texture",
                    param_weights={
                        "dust_density": 0.7,
                        "crackle_amt": 0.5,
                        "resonance": 0.3,
                    },
                ),
            ],
            default_tags={"topology": "noise", "exciter": "continuous", "character": "texture"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "noise",
            "exciter": "continuous",
            "family": "subtractive",
            "method": self._definition.method_id,
        }
        
        noise_type = params.get("noise_type", 0.3)
        if noise_type < 0.25:
            tags["character"] = "white"
        elif noise_type < 0.5:
            tags["character"] = "pink"
        elif noise_type < 0.75:
            tags["character"] = "brown"
        else:
            tags["character"] = "gray"
        
        dust = params.get("dust_density", 0.0)
        if dust > 0.5:
            tags["texture"] = "sparse"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        noise_type = params.get("noise_type", 0.3)
        cutoff = params.get("cutoff_hz", 1500.0)
        res = params.get("resonance", 0.3)
        dust_density = params.get("dust_density", 0.0)
        crackle = params.get("crackle_amt", 0.0)
        
        # Calculate RQ from resonance
        rq = max(0.1, 1.0 - res * 0.9)
        
        # Noise mix weights based on noise_type (0-1)
        # 0.0 = white, 0.33 = pink, 0.66 = brown, 1.0 = gray
        white_w = max(0, 1 - noise_type * 3) if noise_type < 0.33 else 0
        pink_w = max(0, 1 - abs(noise_type - 0.33) * 3) if noise_type < 0.66 else max(0, 1 - (noise_type - 0.33) * 3)
        brown_w = max(0, 1 - abs(noise_type - 0.66) * 3)
        gray_w = max(0, (noise_type - 0.66) * 3) if noise_type > 0.66 else 0
        
        # Normalize
        total = white_w + pink_w + brown_w + gray_w
        if total > 0:
            white_w /= total
            pink_w /= total
            brown_w /= total
            gray_w /= total
        else:
            pink_w = 1.0  # Default to pink
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, noise, dust, crackle, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;

    // Seed for determinism
    RandSeed.ir(1, seed);

    // Read standard params from buses
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\\amplitude]);

    // === NOISE MIX ===
    // Blend different noise types (weights baked in)
    noise = (WhiteNoise.ar * {white_w:.4f}) +
            (PinkNoise.ar * {pink_w:.4f}) +
            (BrownNoise.ar * {brown_w:.4f}) +
            (GrayNoise.ar * {gray_w:.4f});

    // === DUST (velvet-like sparse impulses) ===
    dust = Dust2.ar({20 + dust_density * 500:.1f}) * {dust_density:.4f};
    noise = noise + dust;

    // === CRACKLE (chaotic texture) ===
    crackle = Crackle.ar(1.5 + ({crackle:.4f} * 0.4)) * {crackle:.4f} * 0.3;
    noise = noise + crackle;

    sig = noise;

    // Boost level (noise is naturally quiet after filtering)
    sig = sig * 2;

    // === FILTER ===
    // Use baked cutoff as base, modulated by filter bus
    sig = ~multiFilter.(sig, filterType, filterFreq.min({cutoff:.1f}), rq * {rq:.4f});

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.3);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  ✓ {synthdef_name} loaded".postln;
'''
    
    def generate_json(self, display_name: str, synthdef_name: str) -> Dict:
        return {
            "name": display_name,
            "synthdef": synthdef_name,
            "custom_params": [],  # Phase 1: no custom params exposed
            "output_trim_db": -6.0,
            "midi_retrig": False,  # Noise is continuous
            "pitch_target": None,
        }
