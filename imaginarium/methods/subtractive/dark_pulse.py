"""
imaginarium/methods/subtractive/dark_pulse.py
Dark pulse wave subtractive synthesizer

Character: Dark, hollow, PWM movement
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class DarkPulseTemplate(MethodTemplate):
    """Dark pulse wave with PWM and low-pass filtering."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="subtractive/dark_pulse",
            family="subtractive",
            display_name="Dark Pulse",
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="pulse_width",
                    min_val=0.1,
                    max_val=0.9,
                    default=0.5,
                    curve="linear",
                ),
                ParamAxis(
                    name="pwm_depth",
                    min_val=0.0,
                    max_val=0.4,
                    default=0.1,
                    curve="linear",
                ),
                ParamAxis(
                    name="pwm_rate",
                    min_val=0.1,
                    max_val=4.0,
                    default=0.5,
                    curve="exp",
                ),
                ParamAxis(
                    name="cutoff_hz",
                    min_val=100,
                    max_val=2000,
                    default=800,
                    curve="exp",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.0,
                    max_val=0.8,
                    default=0.2,
                    curve="linear",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="darkness",
                    param_weights={
                        "cutoff_hz": -1.0,
                        "resonance": 0.5,
                    },
                ),
                MacroControl(
                    name="movement",
                    param_weights={
                        "pwm_depth": 1.0,
                        "pwm_rate": 0.8,
                    },
                ),
            ],
            default_tags={"topology": "serial", "oscillator": "pulse", "character": "dark"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "serial",
            "oscillator": "pulse",
            "character": "dark",
            "family": "subtractive",
            "method": self._definition.method_id,
        }
        
        cutoff = params.get("cutoff_hz", 800)
        if cutoff < 400:
            tags["brightness"] = "very_dark"
        elif cutoff < 800:
            tags["brightness"] = "dark"
        else:
            tags["brightness"] = "medium"
        
        pwm = params.get("pwm_depth", 0.1)
        if pwm > 0.2:
            tags["modulation"] = "pwm"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict,
        seed: int,
    ) -> str:
        pw = params.get("pulse_width", 0.5)
        pwm_depth = params.get("pwm_depth", 0.1)
        pwm_rate = params.get("pwm_rate", 0.5)
        cutoff = params.get("cutoff_hz", 800)
        res = params.get("resonance", 0.2)
        
        # Calculate RQ from resonance (higher res = lower rq)
        rq_mult = max(0.2, 1.0 - res * 0.8)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, width, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;

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

    // === PWM PULSE OSCILLATOR ===
    width = {pw:.4f} + (SinOsc.kr({pwm_rate:.4f}) * {pwm_depth:.4f});
    width = width.clip(0.1, 0.9);
    sig = Pulse.ar(freq, width);

    // === FILTER ===
    // Use baked-in cutoff ratio, modulated by filter bus
    sig = ~multiFilter.(sig, filterType, filterFreq.min({cutoff:.1f}), rq * {rq_mult:.4f});

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.15, 0.2);
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
