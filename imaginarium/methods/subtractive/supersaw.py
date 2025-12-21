"""
imaginarium/methods/subtractive/supersaw.py
Supersaw synthesis - stacked detuned saw oscillators

Character: Thick, lush, trance, pads, massive unison
Classic JP-8000 style with 7 detuned oscillators
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class SupersawTemplate(MethodTemplate):
    """Supersaw - stacked detuned oscillators for thick pads."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="subtractive/supersaw",
            family="subtractive",
            display_name="Supersaw",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="detune",
                    min_val=0.001,
                    max_val=0.03,
                    default=0.01,
                    curve="exp",
                ),
                ParamAxis(
                    name="mix",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="linear",
                ),
                ParamAxis(
                    name="cutoff_ratio",
                    min_val=0.1,
                    max_val=1.0,
                    default=0.6,
                    curve="linear",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.0,
                    max_val=0.8,
                    default=0.2,
                    curve="linear",
                ),
                ParamAxis(
                    name="stereo_spread",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="linear",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="thickness",
                    param_weights={
                        "detune": 0.9,
                        "mix": 0.7,
                    },
                ),
                MacroControl(
                    name="brightness",
                    param_weights={
                        "cutoff_ratio": 0.8,
                        "resonance": 0.4,
                    },
                ),
            ],
            default_tags={"topology": "oscillator", "character": "thick"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "oscillator",
            "family": "subtractive",
            "method": self._definition.method_id,
        }
        
        detune = params.get("detune", 0.01)
        if detune > 0.02:
            tags["character"] = "massive"
        elif detune > 0.008:
            tags["character"] = "thick"
        else:
            tags["character"] = "tight"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        detune = params.get("detune", 0.01)
        mix = params.get("mix", 0.7)
        cutoff_ratio = params.get("cutoff_ratio", 0.6)
        res = params.get("resonance", 0.2)
        spread = params.get("stereo_spread", 0.7)
        
        rq = max(0.1, 1.0 - res * 0.9)
        
        # Detune offsets for 7 oscillators (centered on 0)
        offsets = [-3, -2, -1, 0, 1, 2, 3]
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, saws, center, sides, panPos;
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

    // === 7-OSCILLATOR SUPERSAW ===
    // Center oscillator (full volume)
    center = Saw.ar(freq);
    
    // Side oscillators (detuned, progressively panned)
    saws = [
        Saw.ar(freq * (1 + ({detune:.6f} * -3))),  // L3
        Saw.ar(freq * (1 + ({detune:.6f} * -2))),  // L2
        Saw.ar(freq * (1 + ({detune:.6f} * -1))),  // L1
        Saw.ar(freq * (1 + ({detune:.6f} * 1))),   // R1
        Saw.ar(freq * (1 + ({detune:.6f} * 2))),   // R2
        Saw.ar(freq * (1 + ({detune:.6f} * 3)))    // R3
    ];
    
    // Pan positions for stereo spread
    panPos = [-1, -0.66, -0.33, 0.33, 0.66, 1] * {spread:.4f};
    
    // Mix: center vs sides
    sig = (center * (1 - {mix:.4f})) + (Mix.ar(saws) * {mix:.4f} / 6);
    
    // Create stereo image
    sides = Mix.ar(
        saws.collect({{ |saw, i|
            Pan2.ar(saw, panPos[i])
        }})
    ) * {mix:.4f} / 6;
    
    sig = Pan2.ar(center * (1 - {mix:.4f}), 0) + sides;
    sig = sig * 0.5;  // Normalize

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq * {cutoff_ratio:.4f}, rq * {rq:.4f});

    // === OUTPUT CHAIN ===
    // Already stereo from panning above
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
            "output_trim_db": -6.0,
            "midi_retrig": False,
            "pitch_target": None,
        }
