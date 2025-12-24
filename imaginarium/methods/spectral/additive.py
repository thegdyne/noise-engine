"""
imaginarium/methods/spectral/additive.py
Additive synthesis

Character: Mathematical, precise, clean, crystalline, digital
Builds sounds from individual sine wave partials
"""

from typing import Dict

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
            template_version="2",  # Bumped for dynamic params
            param_axes=[
                ParamAxis(
                    name="num_partials",
                    min_val=4.0,
                    max_val=16.0,
                    default=8.0,
                    curve="lin",
                    label="PRT",
                    tooltip="Number of partials (structural)",
                    unit="",
                ),
                ParamAxis(
                    name="odd_even",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="ODD",
                    tooltip="Odd/even harmonic balance",
                    unit="",
                ),
                ParamAxis(
                    name="rolloff",
                    min_val=0.5,
                    max_val=2.0,
                    default=1.0,
                    curve="lin",
                    label="ROL",
                    tooltip="Harmonic amplitude rolloff",
                    unit="",
                ),
                ParamAxis(
                    name="detune_spread",
                    min_val=0.0,
                    max_val=0.015,
                    default=0.003,
                    curve="lin",
                    label="DET",
                    tooltip="Partial detuning spread",
                    unit="",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="lin",
                    label="BRT",
                    tooltip="High partial emphasis",
                    unit="",
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
        # num_partials is STRUCTURAL - baked at generation time
        # (Mix.fill count must be fixed at SynthDef compile time)
        num_p = int(params.get("num_partials", 8.0))
        
        # Get axes for sc_read_expr
        axes = {a.name: a for a in self._definition.param_axes}
        
        # Generate custom param read expressions
        # Note: num_partials (customBus0) is read but primarily for UI feedback
        # The actual partial count is baked
        partials_read = axes["num_partials"].sc_read_expr("customBus0", 0)
        odd_even_read = axes["odd_even"].sc_read_expr("customBus1", 1)
        rolloff_read = axes["rolloff"].sc_read_expr("customBus2", 2)
        detune_read = axes["detune_spread"].sc_read_expr("customBus3", 3)
        bright_read = axes["brightness"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, partials;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var num_partials, odd_even, rolloff, detune_spread, brightness;

    // Seed for determinism
    RandSeed.ir(1, seed);

    // Read standard params from buses
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
    // Note: num_partials is read for completeness but partial count is structural (baked at {num_p})
    {partials_read}
    {odd_even_read}
    {rolloff_read}
    {detune_read}
    {bright_read}

    // === ADDITIVE SYNTHESIS ===
    // Build up partials from sine waves
    // Partial count is structural ({num_p}), other params are dynamic
    partials = Mix.fill({num_p}, {{ |i|
        var harmonic = i + 1;
        var isOdd = (harmonic % 2) == 1;
        var baseAmp = 1 / (harmonic ** rolloff);
        var detuneAmt = 1 + (detune_spread * i * LFNoise1.kr(0.3).range(-1, 1));
        var partialAmp;
        
        // Odd/even control: odd partials get full amp, evens get odd_even amount
        partialAmp = baseAmp * Select.kr(isOdd.asInteger, [odd_even, 1.0]);
        // Brightness boost for higher partials
        partialAmp = partialAmp * (1 + (brightness * harmonic * 0.03));
        
        SinOsc.ar(freq * harmonic * detuneAmt, 0, partialAmp);
    }});
    
    sig = partials / {num_p}.sqrt;  // Normalize

    // === FILTER (light touch for additive) ===
    sig = ~multiFilter.(sig, filterType, filterFreq.min(3000 + (brightness * 5000)), rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
