"""
imaginarium/methods/texture/noise_drone.py
Noise drone synthesis - deep evolving beds and soundscapes

Character: Deep, evolving, immersive, bed-like
Tags: STOCH, drone, ambient, bed
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class NoiseDroneTemplate(MethodTemplate):
    """Deep evolving noise drones for ambient beds."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="texture/noise_drone",
            family="texture",
            display_name="Noise Drone",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="depth",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.6,
                    curve="lin",
                    label="DPT",
                    tooltip="Low frequency emphasis",
                    unit="",
                ),
                ParamAxis(
                    name="movement",
                    min_val=0.01,
                    max_val=2.0,
                    default=0.2,
                    curve="exp",
                    label="MOV",
                    tooltip="Filter modulation rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="texture",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.4,
                    curve="lin",
                    label="TEX",
                    tooltip="Noise color (dark to bright)",
                    unit="",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.0,
                    max_val=0.9,
                    default=0.3,
                    curve="lin",
                    label="RES",
                    tooltip="Filter resonance peaks",
                    unit="",
                ),
                ParamAxis(
                    name="space",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="SPC",
                    tooltip="Stereo width and diffusion",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="darkness",
                    param_weights={
                        "depth": 1.0,
                        "texture": -0.8,
                    },
                ),
                MacroControl(
                    name="animation",
                    param_weights={
                        "movement": 1.0,
                        "resonance": 0.5,
                    },
                ),
            ],
            default_tags={"topology": "noise", "character": "drone", "role": "bed"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "noise",
            "character": "drone",
            "role": "bed",
            "family": "texture",
            "method": self._definition.method_id,
        }
        
        depth = params.get("depth", 0.6)
        if depth > 0.7:
            tags["register"] = "sub"
        elif depth < 0.3:
            tags["register"] = "mid"
        else:
            tags["register"] = "low"
        
        texture = params.get("texture", 0.4)
        if texture > 0.6:
            tags["brightness"] = "bright"
        elif texture < 0.3:
            tags["brightness"] = "dark"
        
        movement = params.get("movement", 0.2)
        if movement > 0.8:
            tags["motion"] = "active"
        elif movement < 0.1:
            tags["motion"] = "static"
        else:
            tags["motion"] = "slow"
        
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
        depth_read = axes["depth"].sc_read_expr("customBus0", 0)
        movement_read = axes["movement"].sc_read_expr("customBus1", 1)
        texture_read = axes["texture"].sc_read_expr("customBus2", 2)
        resonance_read = axes["resonance"].sc_read_expr("customBus3", 3)
        space_read = axes["space"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, movement, texture, resonance, space;
    var noiseL, noiseR, subNoise, midNoise, hiNoise;
    var modL, modR, filterFreqL, filterFreqR;
    var subLayer, bodyLayer, airLayer;

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
    {depth_read}
    {movement_read}
    {texture_read}
    {resonance_read}
    {space_read}

    // === NOISE SOURCES ===
    // Different noise colors for different layers
    subNoise = BrownNoise.ar;
    midNoise = PinkNoise.ar;
    hiNoise = WhiteNoise.ar;
    
    // === SUB LAYER (depth) ===
    // Deep rumbling foundation
    subLayer = LPF.ar(subNoise, 80 + (freq * 0.5));
    subLayer = subLayer + (SinOsc.ar(freq * 0.25) * 0.3);
    subLayer = subLayer * depth * 0.5;
    
    // === BODY LAYER (main drone) ===
    // Slowly modulating filtered noise
    modL = LFNoise2.kr(movement).range(0.5, 2);
    modR = LFNoise2.kr(movement * 1.1).range(0.5, 2);
    
    filterFreqL = freq * modL * (1 + texture);
    filterFreqR = freq * modR * (1 + texture);
    
    // Resonant bandpass filters
    noiseL = RLPF.ar(midNoise, filterFreqL.clip(50, 8000), (1 - resonance).max(0.1));
    noiseR = RLPF.ar(midNoise, filterFreqR.clip(50, 8000), (1 - resonance).max(0.1));
    
    // Add resonant peaks
    noiseL = noiseL + (Resonz.ar(midNoise, filterFreqL * 2, 0.1) * resonance * 0.5);
    noiseR = noiseR + (Resonz.ar(midNoise, filterFreqR * 2, 0.1) * resonance * 0.5);
    
    bodyLayer = [noiseL, noiseR] * 0.4;
    
    // === AIR LAYER (texture/brightness) ===
    // High frequency shimmer
    airLayer = HPF.ar(hiNoise, 2000 + (texture * 4000));
    airLayer = airLayer * LFNoise2.kr(movement * 2).range(0.2, 1);
    airLayer = airLayer * texture * 0.15;
    
    // === MIX ===
    sig = [subLayer, subLayer] + bodyLayer + [airLayer, airLayer];
    
    // === STEREO DIFFUSION ===
    // Add decorrelated modulation for space
    sig[0] = sig[0] + (AllpassN.ar(sig[0], 0.05, LFNoise1.kr(0.3).range(0.01, 0.04), 0.5) * space * 0.3);
    sig[1] = sig[1] + (AllpassN.ar(sig[1], 0.05, LFNoise1.kr(0.31).range(0.01, 0.04), 0.5) * space * 0.3);
    
    // Soft limiting
    sig = sig.tanh;

    // === OUTPUT CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
