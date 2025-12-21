"""
imaginarium/methods/physical/bowed.py
Bowed string physical modeling

Character: Sustained, violin-like, cello, rich harmonics
Uses waveguide-inspired synthesis with friction exciter
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class BowedTemplate(MethodTemplate):
    """Bowed string physical modeling synthesis."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="physical/bowed",
            family="physical",
            display_name="Bowed String",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="bow_pressure",
                    min_val=0.2,
                    max_val=1.0,
                    default=0.5,
                    curve="linear",
                ),
                ParamAxis(
                    name="bow_position",
                    min_val=0.05,
                    max_val=0.2,
                    default=0.1,
                    curve="linear",
                ),
                ParamAxis(
                    name="vibrato_rate",
                    min_val=3.0,
                    max_val=7.0,
                    default=5.0,
                    curve="linear",
                ),
                ParamAxis(
                    name="vibrato_depth",
                    min_val=0.0,
                    max_val=0.02,
                    default=0.008,
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
                    name="intensity",
                    param_weights={
                        "bow_pressure": 0.8,
                        "brightness": 0.5,
                    },
                ),
                MacroControl(
                    name="expression",
                    param_weights={
                        "vibrato_depth": 0.9,
                        "vibrato_rate": 0.3,
                    },
                ),
            ],
            default_tags={"topology": "physical", "exciter": "sustained", "character": "bowed"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "physical",
            "exciter": "sustained",
            "family": "physical",
            "method": self._definition.method_id,
        }
        
        pressure = params.get("bow_pressure", 0.5)
        if pressure > 0.7:
            tags["character"] = "intense"
        elif pressure < 0.35:
            tags["character"] = "gentle"
        else:
            tags["character"] = "expressive"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        pressure = params.get("bow_pressure", 0.5)
        position = params.get("bow_position", 0.1)
        vib_rate = params.get("vibrato_rate", 5.0)
        vib_depth = params.get("vibrato_depth", 0.008)
        bright = params.get("brightness", 0.5)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, vibrato, friction, delay, bowedSig;
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

    // === VIBRATO ===
    vibrato = SinOsc.kr({vib_rate:.4f}).range(1 - {vib_depth:.6f}, 1 + {vib_depth:.6f});
    freq = freq * vibrato;

    // === BOW FRICTION ===
    // Friction noise shaped by bow pressure
    friction = WhiteNoise.ar * {pressure:.4f};
    friction = friction + (PinkNoise.ar * {pressure * 0.5:.4f});
    
    // Bow pressure affects harmonic content
    friction = LPF.ar(friction, {500 + bright * 3000:.1f});
    friction = friction * (1 + ({pressure:.4f} * 2)).tanh;

    // === STRING RESONATOR ===
    // Comb filter simulates string resonance
    delay = CombL.ar(
        friction,
        0.05,
        freq.reciprocal,
        3.0  // Decay time
    );
    
    // Add harmonics via position-dependent filtering
    // Bow position affects which harmonics are emphasized
    bowedSig = delay;
    bowedSig = bowedSig + (CombL.ar(friction, 0.025, (freq * 2).reciprocal, 2.0) * {position:.4f} * 2);
    bowedSig = bowedSig + (CombL.ar(friction, 0.017, (freq * 3).reciprocal, 1.5) * {position:.4f});
    
    sig = bowedSig * 0.4;

    // === BODY RESONANCE ===
    sig = sig + (BPF.ar(sig, freq * 1.5, 0.3) * 0.2);
    sig = sig + (BPF.ar(sig, freq * 2.5, 0.2) * 0.1);

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);

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
            "custom_params": [],
            "output_trim_db": -6.0,
            "midi_retrig": False,  # Sustained sound
            "pitch_target": None,
        }
