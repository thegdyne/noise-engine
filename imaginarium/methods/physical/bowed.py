"""
imaginarium/methods/physical/bowed.py
Bowed string physical modeling

Character: Sustained, violin-like, cello, rich harmonics
Uses waveguide-inspired synthesis with friction exciter
"""

from typing import Dict

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
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="bow_pressure",
                    min_val=0.2,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="PRS",
                    tooltip="Bow pressure intensity",
                    unit="",
                ),
                ParamAxis(
                    name="bow_position",
                    min_val=0.05,
                    max_val=0.2,
                    default=0.1,
                    curve="lin",
                    label="POS",
                    tooltip="Bow position on string",
                    unit="",
                ),
                ParamAxis(
                    name="vibrato_rate",
                    min_val=3.0,
                    max_val=7.0,
                    default=5.0,
                    curve="lin",
                    label="VIB",
                    tooltip="Vibrato rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="vibrato_depth",
                    min_val=0.0,
                    max_val=0.02,
                    default=0.008,
                    curve="lin",
                    label="DEP",
                    tooltip="Vibrato depth",
                    unit="",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="BRT",
                    tooltip="Bow friction brightness",
                    unit="",
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
        # Get axes for sc_read_expr
        axes = {a.name: a for a in self._definition.param_axes}
        
        # Generate custom param read expressions
        pressure_read = axes["bow_pressure"].sc_read_expr("customBus0", 0)
        position_read = axes["bow_position"].sc_read_expr("customBus1", 1)
        vib_rate_read = axes["vibrato_rate"].sc_read_expr("customBus2", 2)
        vib_depth_read = axes["vibrato_depth"].sc_read_expr("customBus3", 3)
        bright_read = axes["brightness"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, vibrato, friction, delay, bowedSig;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bow_pressure, bow_position, vibrato_rate, vibrato_depth, brightness;

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
    {pressure_read}
    {position_read}
    {vib_rate_read}
    {vib_depth_read}
    {bright_read}

    // === VIBRATO ===
    vibrato = SinOsc.kr(vibrato_rate).range(1 - vibrato_depth, 1 + vibrato_depth);
    freq = freq * vibrato;

    // === BOW FRICTION ===
    // Friction noise shaped by bow pressure
    friction = WhiteNoise.ar * bow_pressure;
    friction = friction + (PinkNoise.ar * (bow_pressure * 0.5));
    
    // Bow pressure affects harmonic content
    friction = LPF.ar(friction, 500 + (brightness * 3000));
    friction = friction * (1 + (bow_pressure * 2)).tanh;

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
    bowedSig = bowedSig + (CombL.ar(friction, 0.025, (freq * 2).reciprocal, 2.0) * bow_position * 2);
    bowedSig = bowedSig + (CombL.ar(friction, 0.017, (freq * 3).reciprocal, 1.5) * bow_position);
    
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

"  * {synthdef_name} loaded".postln;
'''
