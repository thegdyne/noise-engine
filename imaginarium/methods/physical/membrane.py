"""
imaginarium/methods/physical/membrane.py
Membrane synthesis - drums, metallic percussion, skins

Character: Percussive, resonant, drums, metallic
Tags: MODEL, membrane, percussion
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class MembraneTemplate(MethodTemplate):
    """Physical membrane model for drum and percussion sounds."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="physical/membrane",
            family="physical",
            display_name="Membrane",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="tension",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="TNS",
                    tooltip="Membrane tension (pitch)",
                    unit="",
                ),
                ParamAxis(
                    name="ring_decay",  # FIXED: renamed from 'decay' to avoid collision
                    min_val=0.05,
                    max_val=3.0,
                    default=0.5,
                    curve="exp",
                    label="DEC",
                    tooltip="Ring decay time",
                    unit="s",
                ),
                ParamAxis(
                    name="strike",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="STK",
                    tooltip="Strike hardness",
                    unit="",
                ),
                ParamAxis(
                    name="metallic",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="lin",
                    label="MTL",
                    tooltip="Metallic/inharmonic partials",
                    unit="",
                ),
                ParamAxis(
                    name="size",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="SIZ",
                    tooltip="Membrane size (body resonance)",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="character",
                    param_weights={
                        "tension": 1.0,
                        "metallic": 0.6,
                    },
                ),
                MacroControl(
                    name="sustain",
                    param_weights={
                        "ring_decay": 1.0,  # FIXED: updated param name
                        "size": 0.5,
                    },
                ),
            ],
            default_tags={"topology": "membrane", "character": "percussive", "role": "accent"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "membrane",
            "character": "percussive",
            "role": "accent",
            "family": "physical",
            "method": self._definition.method_id,
        }
        
        metallic = params.get("metallic", 0.2)
        if metallic > 0.6:
            tags["material"] = "metallic"
        else:
            tags["material"] = "skin"
        
        tension = params.get("tension", 0.5)
        if tension > 0.7:
            tags["pitch"] = "high"
        elif tension < 0.3:
            tags["pitch"] = "low"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        tension_read = axes["tension"].sc_read_expr("customBus0", 0)
        ring_decay_read = axes["ring_decay"].sc_read_expr("customBus1", 1)  # FIXED
        strike_read = axes["strike"].sc_read_expr("customBus2", 2)
        metallic_read = axes["metallic"].sc_read_expr("customBus3", 3)
        size_read = axes["size"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var tension, ring_decay, strike, metallic, size;  // FIXED: renamed memDecay to ring_decay
    var trig, exciter, membrane, modes, modeFreqs, modeAmps;
    var bodyRes, fundFreq;

    // Seed for determinism
    RandSeed.ir(1, seed);

    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\\amplitude]);

    // === READ CUSTOM PARAMS ===
    {tension_read}
    {ring_decay_read}
    {strike_read}
    {metallic_read}
    {size_read}

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        Impulse.ar(0),  // OFF - single impulse for testing
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // === EXCITER (strike) ===
    // Mix of noise burst and click
    exciter = WhiteNoise.ar * EnvGen.ar(Env.perc(0.0001, 0.01 + (strike * 0.02)), trig);
    exciter = exciter + (Impulse.ar(0) * EnvGen.ar(Env.perc(0.0001, 0.005), trig) * strike);
    exciter = HPF.ar(exciter, 100 + (strike * 2000));
    
    // === MEMBRANE MODES ===
    fundFreq = freq * (0.5 + tension);
    
    // Circular membrane modes (ratios from physics)
    // Harmonic: 1.00, 1.59, 2.14, 2.30, 2.65, 2.92...
    // Metallic adds inharmonicity
    modeFreqs = [
        fundFreq,
        fundFreq * (1.59 + (metallic * 0.2)),
        fundFreq * (2.14 + (metallic * 0.4)),
        fundFreq * (2.30 + (metallic * 0.5)),
        fundFreq * (2.65 + (metallic * 0.6)),
        fundFreq * (2.92 + (metallic * 0.7))
    ];
    
    modeAmps = [1, 0.6, 0.4, 0.3, 0.2, 0.15];
    
    // Ring each mode - FIXED: now uses ring_decay which is properly assigned
    modes = [
        Ringz.ar(exciter, modeFreqs[0].clip(50, 12000), ring_decay * 1.0) * modeAmps[0],
        Ringz.ar(exciter, modeFreqs[1].clip(50, 12000), ring_decay * 0.9) * modeAmps[1],
        Ringz.ar(exciter, modeFreqs[2].clip(50, 12000), ring_decay * 0.8) * modeAmps[2],
        Ringz.ar(exciter, modeFreqs[3].clip(50, 12000), ring_decay * 0.7) * modeAmps[3],
        Ringz.ar(exciter, modeFreqs[4].clip(50, 12000), ring_decay * 0.6) * modeAmps[4],
        Ringz.ar(exciter, modeFreqs[5].clip(50, 12000), ring_decay * 0.5) * modeAmps[5]
    ];
    
    membrane = modes.sum * 0.3;
    
    // === BODY RESONANCE ===
    bodyRes = Resonz.ar(exciter, fundFreq * 0.5 * (1 + size), 0.2);
    bodyRes = bodyRes + Resonz.ar(exciter, fundFreq * 0.25, 0.3);
    bodyRes = bodyRes * size * 0.4;
    
    // === MIX ===
    sig = membrane + bodyRes;
    
    // Soft limiting
    sig = sig.tanh;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.05, 0.15);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
