"""
imaginarium/methods/physical/karplus.py
Karplus-Strong string synthesis

Character: Plucked string, guitar-like, bell-like at high frequencies
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class KarplusTemplate(MethodTemplate):
    """Karplus-Strong plucked string synthesis."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="physical/karplus",
            family="physical",
            display_name="Plucked String",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="decay_time",
                    min_val=0.5,
                    max_val=8.0,
                    default=2.0,
                    curve="exp",
                ),
                ParamAxis(
                    name="damping",
                    min_val=0.0,
                    max_val=0.9,
                    default=0.3,
                    curve="linear",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="linear",
                ),
                ParamAxis(
                    name="exciter_color",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="linear",
                ),
                ParamAxis(
                    name="body_size",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="linear",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="material",
                    param_weights={
                        "damping": 0.8,
                        "brightness": -0.8,
                    },
                ),
                MacroControl(
                    name="sustain",
                    param_weights={
                        "decay_time": 1.0,
                        "damping": -0.5,
                    },
                ),
            ],
            default_tags={"topology": "physical", "exciter": "noise", "character": "plucked"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "physical",
            "exciter": "noise",
            "family": "physical",
            "method": self._definition.method_id,
        }
        
        decay = params.get("decay_time", 2.0)
        if decay > 4:
            tags["sustain"] = "long"
        elif decay < 1:
            tags["sustain"] = "short"
        else:
            tags["sustain"] = "medium"
        
        damp = params.get("damping", 0.3)
        if damp > 0.5:
            tags["character"] = "muted"
        else:
            tags["character"] = "plucked"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        decay = params.get("decay_time", 2.0)
        damp = params.get("damping", 0.3)
        bright = params.get("brightness", 0.5)
        exciter = params.get("exciter_color", 0.5)
        body = params.get("body_size", 0.3)
        
        # Coef controls damping (higher = more damping = darker)
        coef = 0.1 + damp * 0.4
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var exc, sig, bodyRes, trig;
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

    // === EXCITER ===
    // Standard Noise Engine trigger selection
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Exciter: noise burst with trigger envelope
    exc = PinkNoise.ar * {0.5 + exciter * 0.5:.4f};
    exc = LPF.ar(exc, filterFreq.min({2000 + bright * 8000:.1f}));
    exc = exc * EnvGen.ar(Env.perc(0.001, 0.05), trig);

    // === KARPLUS-STRONG STRING ===
    sig = Pluck.ar(
        exc,
        trig,
        0.2,
        freq.reciprocal,
        {decay:.4f},
        {coef:.4f}
    );

    // Boost output (Pluck is naturally quiet)
    sig = sig * 3;

    // === BODY RESONANCE ===
    bodyRes = BPF.ar(sig, freq * 1.5, 0.5) * {body * 0.3:.4f};
    bodyRes = bodyRes + (BPF.ar(sig, freq * 2.5, 0.3) * {body * 0.2:.4f});
    sig = sig + bodyRes;

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);

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
            "custom_params": [],  # Phase 1: no custom params exposed
            "output_trim_db": -6.0,
            "midi_retrig": True,  # Plucked sounds need retrigger
            "pitch_target": None,
        }
