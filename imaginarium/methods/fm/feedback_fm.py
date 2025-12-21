"""
imaginarium/methods/fm/feedback_fm.py
Feedback FM synthesis - self-modulating operator

Character: Gritty, aggressive, chaotic, industrial
Single operator with feedback creates rich harmonics to noise
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class FeedbackFMTemplate(MethodTemplate):
    """Feedback FM synthesis - self-modulating oscillator."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/feedback_fm",
            family="fm",
            display_name="Feedback FM",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="feedback",
                    min_val=0.0,
                    max_val=1.5,
                    default=0.5,
                    curve="linear",
                ),
                ParamAxis(
                    name="fb_mod_rate",
                    min_val=0.1,
                    max_val=8.0,
                    default=0.5,
                    curve="exp",
                ),
                ParamAxis(
                    name="fb_mod_depth",
                    min_val=0.0,
                    max_val=1.0,
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
                    name="drive",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="linear",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="chaos",
                    param_weights={
                        "feedback": 0.9,
                        "fb_mod_depth": 0.6,
                        "drive": 0.4,
                    },
                ),
                MacroControl(
                    name="movement",
                    param_weights={
                        "fb_mod_rate": 0.8,
                        "fb_mod_depth": 0.5,
                    },
                ),
            ],
            default_tags={"topology": "fm", "character": "aggressive"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "fm",
            "family": "fm",
            "method": self._definition.method_id,
        }
        
        fb = params.get("feedback", 0.5)
        if fb > 1.0:
            tags["character"] = "chaotic"
        elif fb > 0.6:
            tags["character"] = "aggressive"
        elif fb > 0.3:
            tags["character"] = "gritty"
        else:
            tags["character"] = "warm"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        feedback = params.get("feedback", 0.5)
        fb_mod_rate = params.get("fb_mod_rate", 0.5)
        fb_mod_depth = params.get("fb_mod_depth", 0.3)
        bright = params.get("brightness", 0.5)
        drive = params.get("drive", 0.2)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, fbMod, fbAmount;
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

    // === FEEDBACK FM ===
    // Modulate feedback amount for movement
    fbMod = SinOsc.kr({fb_mod_rate:.4f}).range(1 - {fb_mod_depth:.4f}, 1);
    fbAmount = {feedback:.4f} * fbMod;
    
    // Self-modulating FM oscillator
    // SinOscFB has built-in feedback path
    sig = SinOscFB.ar(freq, fbAmount);
    
    // Add slight detuned copy for thickness
    sig = sig + (SinOscFB.ar(freq * 1.003, fbAmount * 0.9) * 0.3);
    sig = sig * 0.7;  // Normalize mix

    // === DRIVE (waveshaping) ===
    sig = (sig * (1 + ({drive:.4f} * 4))).tanh;
    sig = sig * (1 - ({drive:.4f} * 0.3));  // Compensate gain

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq.min({1000 + bright * 8000:.1f}), rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.2);
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
