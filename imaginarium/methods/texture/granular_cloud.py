"""
imaginarium/methods/texture/granular_cloud.py
Granular cloud synthesis - diffuse atmospheric textures

Character: Atmospheric, shimmering, evolving pads
Tags: GRAIN, texture, ambient
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class GranularCloudTemplate(MethodTemplate):
    """Granular cloud synthesis with density and shimmer control."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="texture/granular_cloud",
            family="texture",
            display_name="Granular Cloud",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="density",
                    min_val=1.0,
                    max_val=100.0,
                    default=30.0,
                    curve="exp",
                    label="DNS",
                    tooltip="Grain density (grains per second)",
                    unit="g/s",
                ),
                ParamAxis(
                    name="grain_size",
                    min_val=0.01,
                    max_val=0.2,
                    default=0.05,
                    curve="exp",
                    label="SIZ",
                    tooltip="Individual grain duration",
                    unit="s",
                ),
                ParamAxis(
                    name="pitch_scatter",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="lin",
                    label="PIT",
                    tooltip="Random pitch variation per grain",
                    unit="",
                ),
                ParamAxis(
                    name="position_jitter",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="JIT",
                    tooltip="Stereo position randomization",
                    unit="",
                ),
                ParamAxis(
                    name="shimmer",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.4,
                    curve="lin",
                    label="SHM",
                    tooltip="High frequency sparkle amount",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="thickness",
                    param_weights={
                        "density": 1.0,
                        "grain_size": 0.6,
                    },
                ),
                MacroControl(
                    name="chaos",
                    param_weights={
                        "pitch_scatter": 1.0,
                        "position_jitter": 0.8,
                    },
                ),
            ],
            default_tags={"topology": "granular", "character": "atmospheric"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "granular",
            "character": "atmospheric",
            "family": "texture",
            "method": self._definition.method_id,
        }
        
        density = params.get("density", 30)
        if density > 60:
            tags["density"] = "dense"
        elif density < 15:
            tags["density"] = "sparse"
        else:
            tags["density"] = "medium"
        
        shimmer = params.get("shimmer", 0.4)
        if shimmer > 0.6:
            tags["brightness"] = "bright"
        elif shimmer < 0.2:
            tags["brightness"] = "dark"
        
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
        density_read = axes["density"].sc_read_expr("customBus0", 0)
        grain_size_read = axes["grain_size"].sc_read_expr("customBus1", 1)
        pitch_scatter_read = axes["pitch_scatter"].sc_read_expr("customBus2", 2)
        position_jitter_read = axes["position_jitter"].sc_read_expr("customBus3", 3)
        shimmer_read = axes["shimmer"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var density, grain_size, pitch_scatter, position_jitter, shimmer;
    var grainTrig, grainFreq, grainEnv, grainSig, grainPan;
    var shimmerSig, cloudL, cloudR;

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
    {density_read}
    {grain_size_read}
    {pitch_scatter_read}
    {position_jitter_read}
    {shimmer_read}

    // === GRANULAR CLOUD ===
    // Trigger grains at density rate with jitter
    grainTrig = Dust.ar(density);
    
    // Pitch varies per grain
    grainFreq = freq * TExpRand.ar(1 - (pitch_scatter * 0.5), 1 + (pitch_scatter * 0.5), grainTrig);
    
    // Each grain is a windowed sine
    grainEnv = EnvGen.ar(Env.sine(grain_size), grainTrig);
    grainSig = SinOsc.ar(grainFreq) * grainEnv;
    
    // Add harmonics for richness
    grainSig = grainSig + (SinOsc.ar(grainFreq * 2) * grainEnv * 0.3);
    grainSig = grainSig + (SinOsc.ar(grainFreq * 3) * grainEnv * 0.15);
    
    // Random pan per grain
    grainPan = TRand.ar(-1 * position_jitter, position_jitter, grainTrig);
    
    // Create stereo from mono grains
    cloudL = grainSig * (1 - grainPan).max(0);
    cloudR = grainSig * (1 + grainPan).max(0);
    
    // === SHIMMER LAYER ===
    // High frequency sparkle
    shimmerSig = Dust2.ar(density * 2) * 0.3;
    shimmerSig = BPF.ar(shimmerSig, freq * 4, 0.5);
    shimmerSig = shimmerSig + (SinOsc.ar(freq * 8 * LFNoise2.kr(2).range(0.98, 1.02)) * 
                               Decay.ar(Dust.ar(density * 0.5), 0.1) * 0.2);
    shimmerSig = shimmerSig * shimmer;
    
    // === MIX ===
    sig = [cloudL + (shimmerSig * LFNoise1.kr(3).range(0.3, 1)), 
           cloudR + (shimmerSig * LFNoise1.kr(3.1).range(0.3, 1))];
    
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
