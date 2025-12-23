"""
imaginarium/methods/fm/phase_mod.py
Phase modulation / phase distortion synthesis

Character: Digital, glassy, CZ-style, evolving harmonics
Tags: PM, phase distortion, digital
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class PhaseModTemplate(MethodTemplate):
    """Phase distortion synthesis inspired by Casio CZ series."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/phase_mod",
            family="fm",
            display_name="Phase Mod",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="distortion",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="DST",
                    tooltip="Phase distortion amount",
                    unit="",
                ),
                ParamAxis(
                    name="waveform",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="WAV",
                    tooltip="Base waveform shape",
                    unit="",
                ),
                ParamAxis(
                    name="mod_rate",
                    min_val=0.1,
                    max_val=8.0,
                    default=1.0,
                    curve="exp",
                    label="RAT",
                    tooltip="Distortion modulation rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="mod_depth",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="MOD",
                    tooltip="Distortion modulation depth",
                    unit="",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="BRT",
                    tooltip="Harmonic brightness",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="intensity",
                    param_weights={
                        "distortion": 1.0,
                        "brightness": 0.6,
                    },
                ),
                MacroControl(
                    name="movement",
                    param_weights={
                        "mod_rate": 0.7,
                        "mod_depth": 1.0,
                    },
                ),
            ],
            default_tags={"topology": "phase_mod", "character": "digital"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "phase_mod",
            "character": "digital",
            "family": "fm",
            "method": self._definition.method_id,
        }
        
        dist = params.get("distortion", 0.5)
        if dist > 0.7:
            tags["intensity"] = "harsh"
        elif dist < 0.3:
            tags["intensity"] = "soft"
        else:
            tags["intensity"] = "moderate"
        
        bright = params.get("brightness", 0.5)
        if bright > 0.7:
            tags["brightness"] = "bright"
        elif bright < 0.3:
            tags["brightness"] = "dark"
        
        mod = params.get("mod_depth", 0.3)
        if mod > 0.5:
            tags["modulation"] = "animated"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        # Get axes for sc_read_expr
        axes = {a.name: a for a in self._definition.param_axes}
        
        # Generate custom param read expressions
        dist_read = axes["distortion"].sc_read_expr("customBus0", 0)
        wave_read = axes["waveform"].sc_read_expr("customBus1", 1)
        rate_read = axes["mod_rate"].sc_read_expr("customBus2", 2)
        depth_read = axes["mod_depth"].sc_read_expr("customBus3", 3)
        bright_read = axes["brightness"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var distortion, waveform, mod_rate, mod_depth, brightness;
    var phase, distPhase, distAmount, modulator;
    var wave1, wave2, harmonics;

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

    // === READ CUSTOM PARAMS ===
    {dist_read}
    {wave_read}
    {rate_read}
    {depth_read}
    {bright_read}

    // === PHASE DISTORTION ===
    // Modulate distortion amount
    modulator = SinOsc.kr(mod_rate).range(1 - mod_depth, 1);
    distAmount = distortion * modulator * 4;
    
    // Generate phase ramp
    phase = Phasor.ar(0, freq * SampleDur.ir, 0, 1);
    
    // Apply phase distortion (CZ-style: warp the phase)
    // This creates the characteristic "resonant" sound
    distPhase = (phase * (1 + distAmount)).mod(1);
    distPhase = distPhase.pow(1 + (distortion * 2));
    
    // === WAVEFORM GENERATION ===
    // Crossfade between sine-like and saw-like based on waveform param
    wave1 = sin(distPhase * 2pi);
    wave2 = (distPhase * 2 - 1);  // Saw-like
    
    sig = XFade2.ar(wave1, wave2, waveform * 2 - 1);
    
    // === BRIGHTNESS HARMONICS ===
    // Add upper harmonics for brightness
    harmonics = sin(distPhase * 4pi) * brightness * 0.3;
    harmonics = harmonics + (sin(distPhase * 6pi) * brightness * 0.15);
    sig = sig + harmonics;
    
    // Add slight detuned layer for thickness
    sig = sig + (SinOsc.ar(freq * 1.002) * 0.1);
    
    // Normalize
    sig = sig * 0.5;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.12, 0.15);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
