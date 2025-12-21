"""
imaginarium/methods/spectral/additive.py
Additive synthesis

Character: Mathematical, precise, clean, crystalline, digital
Builds sounds from individual sine wave partials
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class AdditiveTemplate(MethodTemplate):
    """Additive synthesis - precise harmonic control via sine partials."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="spectral/additive",
            family="spectral",
            display_name="Additive",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="num_partials",
                    min_val=4.0,
                    max_val=16.0,
                    default=8.0,
                    curve="linear",
                ),
                ParamAxis(
                    name="odd_even",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="linear",
                ),
                ParamAxis(
                    name="rolloff",
                    min_val=0.5,
                    max_val=2.0,
                    default=1.0,
                    curve="linear",
                ),
                ParamAxis(
                    name="detune_spread",
                    min_val=0.0,
                    max_val=0.015,
                    default=0.003,
                    curve="linear",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="linear",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="complexity",
                    param_weights={
                        "num_partials": 0.9,
                        "brightness": 0.4,
                    },
                ),
                MacroControl(
                    name="character",
                    param_weights={
                        "odd_even": 0.8,
                        "rolloff": 0.5,
                    },
                ),
            ],
            default_tags={"topology": "additive", "character": "clean"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "additive",
            "family": "spectral",
            "method": self._definition.method_id,
        }
        
        odd_even = params.get("odd_even", 0.5)
        num_partials = params.get("num_partials", 8.0)
        detune = params.get("detune_spread", 0.003)
        
        if odd_even < 0.3:
            tags["character"] = "hollow"
        elif odd_even > 0.7:
            tags["character"] = "full"
        else:
            tags["character"] = "balanced"
        
        if num_partials > 12:
            tags["complexity"] = "rich"
        elif num_partials < 6:
            tags["complexity"] = "simple"
        else:
            tags["complexity"] = "moderate"
        
        if detune > 0.008:
            tags["texture"] = "shimmery"
        else:
            tags["texture"] = "clean"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        num_p = int(params.get("num_partials", 8.0))
        odd_even = params.get("odd_even", 0.5)
        rolloff = params.get("rolloff", 1.0)
        detune = params.get("detune_spread", 0.003)
        bright = params.get("brightness", 0.7)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, partials;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;

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

    // === ADDITIVE SYNTHESIS ===
    // Build up partials from sine waves
    partials = Mix.fill({num_p}, {{ |i|
        var harmonic = i + 1;
        var isOdd = (harmonic % 2) == 1;
        var partialAmp = 1 / (harmonic ** {rolloff:.4f});
        var detuneAmt = 1 + ({detune:.6f} * i * LFNoise1.kr(0.3).range(-1, 1));
        
        // Odd/even control
        partialAmp = partialAmp * (isOdd.asInteger.max({odd_even:.4f}));
        // Brightness boost for higher partials
        partialAmp = partialAmp * (1 + ({bright:.4f} * harmonic * 0.03));
        
        SinOsc.ar(freq * harmonic * detuneAmt, 0, partialAmp);
    }});
    
    sig = partials / {num_p}.sqrt;  // Normalize

    // === FILTER (light touch for additive) ===
    sig = ~multiFilter.(sig, filterType, filterFreq.min({3000 + bright * 5000:.1f}), rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.2);
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
            "custom_params": [],
            "output_trim_db": -3.0,
            "midi_retrig": False,
            "pitch_target": None,
        }
