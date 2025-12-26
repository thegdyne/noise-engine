"""
imaginarium/methods/physical/tube.py
Tube resonance synthesis - wind instruments, pipes, breath

Character: Breathy, hollow, wind-like, organic
Tags: MODEL, tube, wind, breath
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class TubeTemplate(MethodTemplate):
    """Physical tube/pipe model for wind-like sounds."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="physical/tube",
            family="physical",
            display_name="Tube",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="breath",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="BRH",
                    tooltip="Breath/air noise amount",
                    unit="",
                ),
                ParamAxis(
                    name="embouchure",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="EMB",
                    tooltip="Lip/edge tightness",
                    unit="",
                ),
                ParamAxis(
                    name="length",
                    min_val=0.3,
                    max_val=3.0,
                    default=1.0,
                    curve="exp",
                    label="LEN",
                    tooltip="Tube length multiplier",
                    unit="x",
                ),
                ParamAxis(
                    name="flare",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="FLR",
                    tooltip="Bell/flare amount",
                    unit="",
                ),
                ParamAxis(
                    name="flutter",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="lin",
                    label="FLT",
                    tooltip="Pitch flutter/vibrato",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="airiness",
                    param_weights={
                        "breath": 1.0,
                        "flutter": 0.5,
                    },
                ),
                MacroControl(
                    name="resonance",
                    param_weights={
                        "embouchure": 0.8,
                        "flare": 0.6,
                    },
                ),
            ],
            default_tags={"topology": "tube", "character": "breathy"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "tube",
            "character": "breathy",
            "family": "physical",
            "method": self._definition.method_id,
        }
        
        breath = params.get("breath", 0.5)
        if breath > 0.7:
            tags["texture"] = "airy"
        elif breath < 0.3:
            tags["texture"] = "pure"
        
        flare = params.get("flare", 0.3)
        if flare > 0.6:
            tags["shape"] = "bell"
        else:
            tags["shape"] = "cylindrical"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        breath_read = axes["breath"].sc_read_expr("customBus0", 0)
        embouchure_read = axes["embouchure"].sc_read_expr("customBus1", 1)
        length_read = axes["length"].sc_read_expr("customBus2", 2)
        flare_read = axes["flare"].sc_read_expr("customBus3", 3)
        flutter_read = axes["flutter"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var breath, embouchure, length, flare, flutter;
    var exciter, tubeFreq, tube, delayTime, feedback;
    var flutterMod, breathNoise, harmonic1, harmonic2;
    var bellFilter;

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
    {breath_read}
    {embouchure_read}
    {length_read}
    {flare_read}
    {flutter_read}

    // === FLUTTER/VIBRATO ===
    flutterMod = 1 + (SinOsc.kr(5 + LFNoise1.kr(0.5).range(-1, 1)) * flutter * 0.02);
    flutterMod = flutterMod + (LFNoise2.kr(2) * flutter * 0.005);
    
    // === TUBE FREQUENCY ===
    tubeFreq = freq / length * flutterMod;
    delayTime = (1 / tubeFreq).clip(0.0001, 0.05);
    
    // === EXCITER (breath + edge tone) ===
    breathNoise = PinkNoise.ar * breath;
    breathNoise = BPF.ar(breathNoise, tubeFreq * 2, 0.5);
    
    // Edge tone oscillator (embouchure controls harmonic content)
    exciter = Pulse.ar(tubeFreq, embouchure.linlin(0, 1, 0.3, 0.5)) * (1 - breath);
    exciter = exciter + (SinOsc.ar(tubeFreq) * 0.3);
    exciter = exciter + breathNoise;
    
    // === TUBE RESONATOR (delay-based waveguide) ===
    feedback = embouchure.linlin(0, 1, 0.7, 0.95);
    
    tube = exciter + (LocalIn.ar(1) * feedback);
    tube = DelayC.ar(tube, 0.05, delayTime);
    tube = LPF.ar(tube, tubeFreq * (4 + (embouchure * 8)));  // Brighter with tight embouchure
    tube = LeakDC.ar(tube);
    LocalOut.ar(tube);
    
    // === HARMONICS ===
    harmonic1 = SinOsc.ar(tubeFreq * 2) * 0.2 * embouchure;
    harmonic2 = SinOsc.ar(tubeFreq * 3) * 0.1 * embouchure;
    
    tube = tube + harmonic1 + harmonic2;
    
    // === BELL/FLARE FILTER ===
    // Flare boosts high frequencies like a horn bell
    bellFilter = RLPF.ar(tube, (2000 + (flare * 6000)).clip(100, 12000), 0.5 - (flare * 0.3));
    tube = (tube * (1 - flare)) + (bellFilter * flare * 1.5);
    
    // Add breath texture to output
    tube = tube + (breathNoise * 0.3);
    
    sig = tube;
    
    // Soft limiting
    sig = sig.tanh * 0.6;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
