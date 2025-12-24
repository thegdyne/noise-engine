"""
imaginarium/methods/spectral/harmonic_series.py
Harmonic series synthesis - pure overtone control

Character: Pure, organ-like, bell-like, crystalline
Tags: SPEC, additive, harmonics, pure
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class HarmonicSeriesTemplate(MethodTemplate):
    """Harmonic series synthesis with controllable overtones."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="spectral/harmonic_series",
            family="spectral",
            display_name="Harmonic Series",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="partials",
                    min_val=1.0,
                    max_val=16.0,
                    default=8.0,
                    curve="lin",
                    label="PRT",
                    tooltip="Number of partials",
                    unit="",
                ),
                ParamAxis(
                    name="slope",
                    min_val=-2.0,
                    max_val=0.0,
                    default=-1.0,
                    curve="lin",
                    label="SLP",
                    tooltip="Amplitude rolloff per partial",
                    unit="dB",
                ),
                ParamAxis(
                    name="odd_even",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="ODD",
                    tooltip="Odd vs even harmonic balance",
                    unit="",
                ),
                ParamAxis(
                    name="stretch",
                    min_val=0.99,
                    max_val=1.02,
                    default=1.0,
                    curve="lin",
                    label="STR",
                    tooltip="Inharmonicity stretch",
                    unit="x",
                ),
                ParamAxis(
                    name="shimmer",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.1,
                    curve="lin",
                    label="SHM",
                    tooltip="Per-partial vibrato",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="brightness",
                    param_weights={
                        "partials": 0.8,
                        "slope": 1.0,
                    },
                ),
                MacroControl(
                    name="character",
                    param_weights={
                        "odd_even": 1.0,
                        "stretch": 0.5,
                    },
                ),
            ],
            default_tags={"topology": "additive", "character": "pure"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "additive",
            "character": "pure",
            "family": "spectral",
            "method": self._definition.method_id,
        }
        
        odd_even = params.get("odd_even", 0.5)
        if odd_even > 0.7:
            tags["timbre"] = "hollow"  # More odd = square-ish
        elif odd_even < 0.3:
            tags["timbre"] = "even"  # More even = octave-ish
        
        stretch = params.get("stretch", 1.0)
        if stretch > 1.01 or stretch < 0.995:
            tags["quality"] = "inharmonic"
        else:
            tags["quality"] = "harmonic"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        partials_read = axes["partials"].sc_read_expr("customBus0", 0)
        slope_read = axes["slope"].sc_read_expr("customBus1", 1)
        odd_even_read = axes["odd_even"].sc_read_expr("customBus2", 2)
        stretch_read = axes["stretch"].sc_read_expr("customBus3", 3)
        shimmer_read = axes["shimmer"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var partials, slope, odd_even, stretch, shimmer;
    var numPartials, partial, partialFreq, partialAmp, isOdd, vibrato;
    var p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15, p16;

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
    {partials_read}
    {slope_read}
    {odd_even_read}
    {stretch_read}
    {shimmer_read}

    numPartials = partials.round;
    
    // === PARTIALS (unrolled for f-string safety) ===
    // Partial n: freq * n^stretch, amp = baseAmp * (slope^n) * odd/even weighting
    
    // Partial 1 (fundamental)
    vibrato = SinOsc.kr(4 + LFNoise1.kr(0.5).range(-0.5, 0.5), Rand(0, 2pi));
    p1 = SinOsc.ar(freq * (1 ** stretch) * (1 + (vibrato * shimmer * 0.01)));
    p1 = p1 * 1.0;  // Fundamental full amplitude
    
    // Partial 2
    vibrato = SinOsc.kr(4.1 + LFNoise1.kr(0.5).range(-0.5, 0.5), Rand(0, 2pi));
    p2 = SinOsc.ar(freq * (2 ** stretch) * (1 + (vibrato * shimmer * 0.01)));
    p2 = p2 * slope.dbamp * (1 - odd_even) * (numPartials >= 2);  // Even
    
    // Partial 3
    vibrato = SinOsc.kr(4.2 + LFNoise1.kr(0.5).range(-0.5, 0.5), Rand(0, 2pi));
    p3 = SinOsc.ar(freq * (3 ** stretch) * (1 + (vibrato * shimmer * 0.01)));
    p3 = p3 * (slope * 2).dbamp * odd_even * (numPartials >= 3);  // Odd
    
    // Partial 4
    vibrato = SinOsc.kr(4.3 + LFNoise1.kr(0.5).range(-0.5, 0.5), Rand(0, 2pi));
    p4 = SinOsc.ar(freq * (4 ** stretch) * (1 + (vibrato * shimmer * 0.01)));
    p4 = p4 * (slope * 3).dbamp * (1 - odd_even) * (numPartials >= 4);
    
    // Partial 5
    vibrato = SinOsc.kr(4.4 + LFNoise1.kr(0.5).range(-0.5, 0.5), Rand(0, 2pi));
    p5 = SinOsc.ar(freq * (5 ** stretch) * (1 + (vibrato * shimmer * 0.01)));
    p5 = p5 * (slope * 4).dbamp * odd_even * (numPartials >= 5);
    
    // Partial 6
    vibrato = SinOsc.kr(4.5 + LFNoise1.kr(0.5).range(-0.5, 0.5), Rand(0, 2pi));
    p6 = SinOsc.ar(freq * (6 ** stretch) * (1 + (vibrato * shimmer * 0.01)));
    p6 = p6 * (slope * 5).dbamp * (1 - odd_even) * (numPartials >= 6);
    
    // Partial 7
    vibrato = SinOsc.kr(4.6 + LFNoise1.kr(0.5).range(-0.5, 0.5), Rand(0, 2pi));
    p7 = SinOsc.ar(freq * (7 ** stretch) * (1 + (vibrato * shimmer * 0.01)));
    p7 = p7 * (slope * 6).dbamp * odd_even * (numPartials >= 7);
    
    // Partial 8
    vibrato = SinOsc.kr(4.7 + LFNoise1.kr(0.5).range(-0.5, 0.5), Rand(0, 2pi));
    p8 = SinOsc.ar(freq * (8 ** stretch) * (1 + (vibrato * shimmer * 0.01)));
    p8 = p8 * (slope * 7).dbamp * (1 - odd_even) * (numPartials >= 8);
    
    // Higher partials (simplified)
    p9 = SinOsc.ar(freq * (9 ** stretch)) * (slope * 8).dbamp * odd_even * (numPartials >= 9);
    p10 = SinOsc.ar(freq * (10 ** stretch)) * (slope * 9).dbamp * (1 - odd_even) * (numPartials >= 10);
    p11 = SinOsc.ar(freq * (11 ** stretch)) * (slope * 10).dbamp * odd_even * (numPartials >= 11);
    p12 = SinOsc.ar(freq * (12 ** stretch)) * (slope * 11).dbamp * (1 - odd_even) * (numPartials >= 12);
    p13 = SinOsc.ar(freq * (13 ** stretch)) * (slope * 12).dbamp * odd_even * (numPartials >= 13);
    p14 = SinOsc.ar(freq * (14 ** stretch)) * (slope * 13).dbamp * (1 - odd_even) * (numPartials >= 14);
    p15 = SinOsc.ar(freq * (15 ** stretch)) * (slope * 14).dbamp * odd_even * (numPartials >= 15);
    p16 = SinOsc.ar(freq * (16 ** stretch)) * (slope * 15).dbamp * (1 - odd_even) * (numPartials >= 16);
    
    // Sum all partials
    sig = p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9 + p10 + p11 + p12 + p13 + p14 + p15 + p16;
    
    // Normalize
    sig = sig / (numPartials.sqrt.max(1));

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.05, 0.15);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
