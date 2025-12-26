"""
imaginarium/methods/fm/ratio_stack.py
Ratio stack FM synthesis - multiple stacked operators

Character: Complex, evolving, DX7-style, organ-like to metallic
Uses 3 modulators with different ratios stacked on carrier
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class RatioStackTemplate(MethodTemplate):
    """Multi-operator FM with stacked ratios."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/ratio_stack",
            family="fm",
            display_name="Ratio Stack FM",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="ratio_spread",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="SPR",
                    tooltip="Harmonic to inharmonic ratio spread",
                    unit="",
                ),
                ParamAxis(
                    name="index_1",
                    min_val=0.5,
                    max_val=6.0,
                    default=2.0,
                    curve="exp",
                    label="IX1",
                    tooltip="Modulator 1 index",
                    unit="",
                ),
                ParamAxis(
                    name="index_2",
                    min_val=0.2,
                    max_val=4.0,
                    default=1.5,
                    curve="exp",
                    label="IX2",
                    tooltip="Modulator 2 index",
                    unit="",
                ),
                ParamAxis(
                    name="index_3",
                    min_val=0.1,
                    max_val=3.0,
                    default=0.8,
                    curve="exp",
                    label="IX3",
                    tooltip="Modulator 3 index",
                    unit="",
                ),
                ParamAxis(
                    name="mod_decay",
                    min_val=0.1,
                    max_val=4.0,
                    default=1.0,
                    curve="exp",
                    label="DEC",
                    tooltip="Modulation index decay time",
                    unit="s",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="complexity",
                    param_weights={
                        "index_1": 0.7,
                        "index_2": 0.8,
                        "index_3": 0.9,
                    },
                ),
                MacroControl(
                    name="harmonic",
                    param_weights={
                        "ratio_spread": -0.8,  # Lower = more harmonic
                    },
                ),
            ],
            default_tags={"topology": "fm", "character": "complex"},
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
        
        spread = params.get("ratio_spread", 0.5)
        if spread < 0.3:
            tags["character"] = "harmonic"
        elif spread < 0.6:
            tags["character"] = "complex"
        else:
            tags["character"] = "metallic"
        
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
        spread_read = axes["ratio_spread"].sc_read_expr("customBus0", 0)
        idx1_read = axes["index_1"].sc_read_expr("customBus1", 1)
        idx2_read = axes["index_2"].sc_read_expr("customBus2", 2)
        idx3_read = axes["index_3"].sc_read_expr("customBus3", 3)
        decay_read = axes["mod_decay"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, mod1, mod2, mod3, modEnv, car;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ratio_spread, index_1, index_2, index_3, mod_decay;
    var r1, r2, r3;

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
    {spread_read}
    {idx1_read}
    {idx2_read}
    {idx3_read}
    {decay_read}

    // Calculate ratios based on spread
    // spread=0: pure harmonic (1, 2, 3)
    // spread=1: inharmonic (1, 2.37, 4.19)
    r1 = 1.0;
    r2 = 2.0 + (ratio_spread * 0.37);
    r3 = 3.0 + (ratio_spread * 1.19);

    // === MODULATOR ENVELOPE ===
    // Indices decay over time for evolving timbre
    modEnv = EnvGen.kr(Env.perc(0.01, mod_decay), doneAction: 0);
    modEnv = modEnv.linlin(0, 1, 0.3, 1);  // Never fully decay

    // === MODULATORS ===
    // Three stacked modulators with different ratios
    mod1 = SinOsc.ar(freq * r1) * index_1 * modEnv * freq;
    mod2 = SinOsc.ar(freq * r2) * index_2 * modEnv * freq;
    mod3 = SinOsc.ar(freq * r3) * index_3 * modEnv * freq;

    // === CARRIER ===
    // Sum all modulators into carrier phase
    car = SinOsc.ar(freq + mod1 + mod2 + mod3);
    sig = car;

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.15, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
