"""
imaginarium/methods/fm/ring_mod.py
Ring modulation synthesis

Character: Metallic, atonal, sci-fi, clangy, dissonant
Multiplies two signals creating sum/difference sidebands
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class RingModTemplate(MethodTemplate):
    """Ring modulation - multiply carrier and modulator."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/ring_mod",
            family="fm",
            display_name="Ring Mod",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="mod_ratio",
                    min_val=0.5,
                    max_val=4.0,
                    default=1.5,
                    curve="linear",
                ),
                ParamAxis(
                    name="mod_detune",
                    min_val=0.0,
                    max_val=50.0,
                    default=5.0,
                    curve="linear",
                ),
                ParamAxis(
                    name="mix",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="linear",
                ),
                ParamAxis(
                    name="mod_shape",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.0,
                    curve="linear",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="linear",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="dissonance",
                    param_weights={
                        "mod_detune": 0.9,
                        "mod_ratio": 0.5,
                    },
                ),
                MacroControl(
                    name="metallic",
                    param_weights={
                        "mix": 0.8,
                        "brightness": 0.6,
                    },
                ),
            ],
            default_tags={"topology": "ring_mod", "character": "metallic"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "ring_mod",
            "family": "fm",
            "method": self._definition.method_id,
        }
        
        detune = params.get("mod_detune", 5.0)
        mix = params.get("mix", 0.7)
        
        if detune > 20 or mix > 0.8:
            tags["character"] = "atonal"
        elif detune > 5:
            tags["character"] = "metallic"
        else:
            tags["character"] = "harmonic"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        ratio = params.get("mod_ratio", 1.5)
        detune = params.get("mod_detune", 5.0)
        mix = params.get("mix", 0.7)
        shape = params.get("mod_shape", 0.0)
        bright = params.get("brightness", 0.5)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, carrier, modulator, ringMod, dry;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var modFreq;

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

    // === CARRIER ===
    // Rich carrier with slight detune for thickness
    carrier = Saw.ar(freq) * 0.7;
    carrier = carrier + (Pulse.ar(freq * 1.001, 0.5) * 0.3);

    // === MODULATOR ===
    // Modulator frequency with ratio and detune
    modFreq = (freq * {ratio:.4f}) + {detune:.4f};
    
    // Shape: 0 = sine (pure), 1 = saw (harsh)
    modulator = SelectX.ar({shape:.4f}, [
        SinOsc.ar(modFreq),
        LFSaw.ar(modFreq)
    ]);

    // === RING MODULATION ===
    // Multiply carrier * modulator
    ringMod = carrier * modulator;

    // === MIX ===
    dry = carrier;
    sig = (dry * (1 - {mix:.4f})) + (ringMod * {mix:.4f});

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq.min({2000 + bright * 6000:.1f}), rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.3);
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
