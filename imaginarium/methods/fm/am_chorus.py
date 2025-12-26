"""
imaginarium/methods/fm/am_chorus.py
AM Chorus synthesis - amplitude modulation with detuned layers

Character: Lush, shimmering, pad-like, ensemble
Tags: AM, chorus, ensemble, pads
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class AMChorusTemplate(MethodTemplate):
    """Amplitude modulation with detuned chorus layers for lush pads."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/am_chorus",
            family="fm",
            display_name="AM Chorus",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="mod_depth",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="DEP",
                    tooltip="AM modulation depth",
                    unit="",
                ),
                ParamAxis(
                    name="mod_rate",
                    min_val=0.1,
                    max_val=20.0,
                    default=3.0,
                    curve="exp",
                    label="RAT",
                    tooltip="AM modulation rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="detune",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="DTN",
                    tooltip="Voice detuning amount",
                    unit="",
                ),
                ParamAxis(
                    name="voices",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="VOC",
                    tooltip="Number of chorus voices",
                    unit="",
                ),
                ParamAxis(
                    name="shimmer",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.4,
                    curve="lin",
                    label="SHM",
                    tooltip="High frequency shimmer",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="movement",
                    param_weights={
                        "mod_depth": 0.8,
                        "mod_rate": 1.0,
                    },
                ),
                MacroControl(
                    name="richness",
                    param_weights={
                        "detune": 1.0,
                        "voices": 0.8,
                        "shimmer": 0.5,
                    },
                ),
            ],
            default_tags={"topology": "am", "character": "lush", "role": "bed"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "am",
            "character": "lush",
            "role": "bed",
            "family": "fm",
            "method": self._definition.method_id,
        }
        
        detune = params.get("detune", 0.3)
        if detune > 0.6:
            tags["width"] = "wide"
        elif detune < 0.2:
            tags["width"] = "tight"
        
        mod_rate = params.get("mod_rate", 3.0)
        if mod_rate > 10:
            tags["motion"] = "fast"
        elif mod_rate < 1:
            tags["motion"] = "slow"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        mod_depth_read = axes["mod_depth"].sc_read_expr("customBus0", 0)
        mod_rate_read = axes["mod_rate"].sc_read_expr("customBus1", 1)
        detune_read = axes["detune"].sc_read_expr("customBus2", 2)
        voices_read = axes["voices"].sc_read_expr("customBus3", 3)
        shimmer_read = axes["shimmer"].sc_read_expr("customBus4", 4)
        
        # FIXED: Use snake_case variable names to match axis names
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mod_depth, mod_rate, detune, voices, shimmer;
    var carrier, modulator, detuneAmt;

    // Seed for determinism
    RandSeed.ir(1, seed);

    // Read standard params
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\\amplitude]);

    // === READ CUSTOM PARAMS ===
    {mod_depth_read}
    {mod_rate_read}
    {detune_read}
    {voices_read}
    {shimmer_read}

    // === SYNTHESIS ===
    // Simple detuned carrier with AM
    detuneAmt = detune * 0.02;  // Max 2% detune
    
    // Stereo carrier - left and right slightly detuned
    carrier = SinOsc.ar(freq * [1 - detuneAmt, 1 + detuneAmt]);
    
    // Add voices layer
    carrier = carrier + (SinOsc.ar(freq * 2 * [1.002, 0.998]) * voices * 0.3);
    
    // AM modulator
    modulator = SinOsc.kr(mod_rate).range(1 - mod_depth, 1);
    
    // Apply AM
    sig = carrier * modulator;
    
    // Shimmer - octave up
    sig = sig + (SinOsc.ar(freq * 2) * shimmer * 0.2);
    
    // Soft saturation
    sig = (sig * 1.2).tanh * 0.6;

    // === OUTPUT CHAIN (per GENERATOR_SPEC.md) ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
