"""
imaginarium/methods/fm/simple_fm.py
Simple 2-operator FM synthesis

Character: Bell-like, metallic, harmonic to inharmonic
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class SimpleFMTemplate(MethodTemplate):
    """Simple 2-operator FM with ratio and index control."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/simple_fm",
            family="fm",
            display_name="Simple FM",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="ratio",
                    min_val=0.5,
                    max_val=8.0,
                    default=2.0,
                    curve="linear",
                ),
                ParamAxis(
                    name="index",
                    min_val=0.0,
                    max_val=10.0,
                    default=3.0,
                    curve="linear",
                ),
                ParamAxis(
                    name="index_decay",
                    min_val=0.1,
                    max_val=4.0,
                    default=1.0,
                    curve="exp",
                ),
                ParamAxis(
                    name="mod_env_amt",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
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
                    name="metallic",
                    param_weights={
                        "ratio": 0.8,
                        "index": 0.7,
                    },
                ),
                MacroControl(
                    name="evolve",
                    param_weights={
                        "mod_env_amt": 1.0,
                        "index_decay": 0.6,
                    },
                ),
            ],
            default_tags={"topology": "fm", "oscillator": "sine", "character": "metallic"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "fm",
            "oscillator": "sine",
            "family": "fm",
            "method": self._definition.method_id,
        }
        
        ratio = params.get("ratio", 2.0)
        # Check if ratio is close to integer (harmonic)
        if abs(ratio - round(ratio)) < 0.1:
            tags["character"] = "harmonic"
        else:
            tags["character"] = "inharmonic"
        
        index = params.get("index", 3.0)
        if index > 6:
            tags["timbre"] = "bright"
        elif index < 2:
            tags["timbre"] = "pure"
        else:
            tags["timbre"] = "medium"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        ratio = params.get("ratio", 2.0)
        index = params.get("index", 3.0)
        index_decay = params.get("index_decay", 1.0)
        mod_env = params.get("mod_env_amt", 0.5)
        bright = params.get("brightness", 0.5)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var mod, car, modEnv, sig, idx;
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

    // === FM SYNTHESIS ===
    // Modulator envelope (controls index over time)
    modEnv = EnvGen.kr(Env.perc(0.01, {index_decay:.4f}));
    modEnv = (modEnv * {mod_env:.4f}) + (1 - {mod_env:.4f});
    
    // Dynamic modulation index
    idx = {index:.4f} * modEnv;
    
    // Modulator oscillator
    mod = SinOsc.ar(freq * {ratio:.4f}) * idx * freq;
    
    // Carrier oscillator (frequency modulated)
    car = SinOsc.ar(freq + mod);
    
    sig = car;

    // === FILTER ===
    // Apply brightness filter, modulated by filter bus
    sig = ~multiFilter.(sig, filterType, filterFreq.min({1000 + bright * 6000:.1f}), rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.15);
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
            "midi_retrig": False,
            "pitch_target": None,
        }
