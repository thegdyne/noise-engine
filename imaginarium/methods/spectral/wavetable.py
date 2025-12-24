"""
imaginarium/methods/spectral/wavetable.py
Wavetable synthesis - morphing between waveforms

Character: Evolving, versatile, modern, smooth
Tags: SPEC, wavetable, morph, digital
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class WavetableTemplate(MethodTemplate):
    """Wavetable synthesis with morphing between waveforms."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="spectral/wavetable",
            family="spectral",
            display_name="Wavetable",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="position",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.0,
                    curve="lin",
                    label="POS",
                    tooltip="Wavetable position (morph)",
                    unit="",
                ),
                ParamAxis(
                    name="morph_rate",
                    min_val=0.01,
                    max_val=5.0,
                    default=0.2,
                    curve="exp",
                    label="MRT",
                    tooltip="Auto-morph LFO rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="morph_depth",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="MDP",
                    tooltip="Auto-morph amount",
                    unit="",
                ),
                ParamAxis(
                    name="harmonics",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="HRM",
                    tooltip="Harmonic richness",
                    unit="",
                ),
                ParamAxis(
                    name="detune",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.1,
                    curve="lin",
                    label="DTN",
                    tooltip="Unison detune amount",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="movement",
                    param_weights={
                        "morph_rate": 1.0,
                        "morph_depth": 0.8,
                    },
                ),
                MacroControl(
                    name="richness",
                    param_weights={
                        "harmonics": 1.0,
                        "detune": 0.6,
                    },
                ),
            ],
            default_tags={"topology": "wavetable", "character": "evolving"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "wavetable",
            "character": "evolving",
            "family": "spectral",
            "method": self._definition.method_id,
        }
        
        morph_rate = params.get("morph_rate", 0.2)
        if morph_rate > 1.0:
            tags["motion"] = "active"
        elif morph_rate < 0.1:
            tags["motion"] = "static"
        
        harmonics = params.get("harmonics", 0.5)
        if harmonics > 0.7:
            tags["brightness"] = "bright"
        elif harmonics < 0.3:
            tags["brightness"] = "dark"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        position_read = axes["position"].sc_read_expr("customBus0", 0)
        morph_rate_read = axes["morph_rate"].sc_read_expr("customBus1", 1)
        morph_depth_read = axes["morph_depth"].sc_read_expr("customBus2", 2)
        harmonics_read = axes["harmonics"].sc_read_expr("customBus3", 3)
        detune_read = axes["detune"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var position, morph_rate, morph_depth, harmonics, detune;
    var morphLFO, pos, wave1, wave2, wave3, wave4;
    var osc1, osc2, osc3, detuneAmt;

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
    {position_read}
    {morph_rate_read}
    {morph_depth_read}
    {harmonics_read}
    {detune_read}

    // === MORPH LFO ===
    morphLFO = SinOsc.kr(morph_rate).range(0, morph_depth);
    pos = (position + morphLFO).wrap(0, 1);
    
    // === WAVETABLE (simulated with crossfading waveforms) ===
    // 4 waveforms: sine -> tri -> saw -> pulse
    wave1 = SinOsc.ar(freq);
    wave2 = LFTri.ar(freq);
    wave3 = Saw.ar(freq);
    wave4 = Pulse.ar(freq, 0.5);
    
    // Crossfade based on position (0-1 spans all 4)
    osc1 = SelectX.ar(pos * 3, [wave1, wave2, wave3, wave4]);
    
    // === DETUNED UNISON ===
    detuneAmt = detune * 0.02;
    
    wave1 = SinOsc.ar(freq * (1 - detuneAmt));
    wave2 = LFTri.ar(freq * (1 - detuneAmt));
    wave3 = Saw.ar(freq * (1 - detuneAmt));
    wave4 = Pulse.ar(freq * (1 - detuneAmt), 0.5);
    osc2 = SelectX.ar(pos * 3, [wave1, wave2, wave3, wave4]);
    
    wave1 = SinOsc.ar(freq * (1 + detuneAmt));
    wave2 = LFTri.ar(freq * (1 + detuneAmt));
    wave3 = Saw.ar(freq * (1 + detuneAmt));
    wave4 = Pulse.ar(freq * (1 + detuneAmt), 0.5);
    osc3 = SelectX.ar(pos * 3, [wave1, wave2, wave3, wave4]);
    
    // Mix with stereo spread
    sig = [osc1 + (osc2 * 0.5), osc1 + (osc3 * 0.5)] / 1.5;
    
    // === HARMONICS (add upper partials) ===
    sig = sig + (SinOsc.ar(freq * 2) * harmonics * 0.3);
    sig = sig + (SinOsc.ar(freq * 3) * harmonics * 0.2);
    sig = sig + (SinOsc.ar(freq * 4) * harmonics * 0.1);
    
    // Normalize
    sig = sig * 0.5;

    // === OUTPUT CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
