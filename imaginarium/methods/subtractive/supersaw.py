"""
imaginarium/methods/subtractive/supersaw.py
Supersaw synthesis - stacked detuned saw oscillators

Character: Thick, lush, trance, pads, massive unison
Classic JP-8000 style with 7 detuned oscillators
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class SupersawTemplate(MethodTemplate):
    """Supersaw - stacked detuned oscillators for thick pads."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="subtractive/supersaw",
            family="subtractive",
            display_name="Supersaw",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="detune",
                    min_val=0.001,
                    max_val=0.03,
                    default=0.01,
                    curve="exp",
                    label="DET",
                    tooltip="Oscillator detune amount",
                    unit="",
                ),
                ParamAxis(
                    name="mix",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="lin",
                    label="MIX",
                    tooltip="Center vs detuned oscillator balance",
                    unit="",
                ),
                ParamAxis(
                    name="cutoff_ratio",
                    min_val=0.1,
                    max_val=1.0,
                    default=0.6,
                    curve="lin",
                    label="CUT",
                    tooltip="Filter cutoff as ratio of maximum",
                    unit="",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.0,
                    max_val=0.8,
                    default=0.2,
                    curve="lin",
                    label="RES",
                    tooltip="Filter resonance",
                    unit="",
                ),
                ParamAxis(
                    name="stereo_spread",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="lin",
                    label="WID",
                    tooltip="Stereo spread of detuned oscillators",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="thickness",
                    param_weights={
                        "detune": 0.9,
                        "mix": 0.7,
                    },
                ),
                MacroControl(
                    name="brightness",
                    param_weights={
                        "cutoff_ratio": 0.8,
                        "resonance": 0.4,
                    },
                ),
            ],
            default_tags={"topology": "oscillator", "character": "thick"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "oscillator",
            "family": "subtractive",
            "method": self._definition.method_id,
        }
        
        detune = params.get("detune", 0.01)
        if detune > 0.02:
            tags["character"] = "massive"
        elif detune > 0.008:
            tags["character"] = "thick"
        else:
            tags["character"] = "tight"
        
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
        detune_read = axes["detune"].sc_read_expr("customBus0", 0)
        mix_read = axes["mix"].sc_read_expr("customBus1", 1)
        cutoff_read = axes["cutoff_ratio"].sc_read_expr("customBus2", 2)
        res_read = axes["resonance"].sc_read_expr("customBus3", 3)
        spread_read = axes["stereo_spread"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, saws, center, sides, panPos;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var detune, mix, cutoff_ratio, resonance, stereo_spread, rq_scaled;

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
    {detune_read}
    {mix_read}
    {cutoff_read}
    {res_read}
    {spread_read}

    // Calculate RQ from resonance
    rq_scaled = (1.0 - (resonance * 0.9)).max(0.1);

    // === 7-OSCILLATOR SUPERSAW ===
    // Center oscillator (full volume)
    center = Saw.ar(freq);
    
    // Side oscillators (detuned, progressively panned)
    saws = [
        Saw.ar(freq * (1 + (detune * -3))),  // L3
        Saw.ar(freq * (1 + (detune * -2))),  // L2
        Saw.ar(freq * (1 + (detune * -1))),  // L1
        Saw.ar(freq * (1 + (detune * 1))),   // R1
        Saw.ar(freq * (1 + (detune * 2))),   // R2
        Saw.ar(freq * (1 + (detune * 3)))    // R3
    ];
    
    // Pan positions for stereo spread
    panPos = [-1, -0.66, -0.33, 0.33, 0.66, 1] * stereo_spread;
    
    // Mix: center vs sides
    sig = (center * (1 - mix)) + (Mix.ar(saws) * mix / 6);
    
    // Create stereo image
    sides = Mix.ar(
        saws.collect({{ |saw, i|
            Pan2.ar(saw, panPos[i])
        }})
    ) * mix / 6;
    
    sig = Pan2.ar(center * (1 - mix), 0) + sides;
    sig = sig * 0.5;  // Normalize

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq * cutoff_ratio, rq * rq_scaled);

    // === OUTPUT CHAIN ===
    // Already stereo from panning above
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
