"""
imaginarium/methods/subtractive/noise_filtered.py
Filtered noise synthesis with multiple noise types

Character: Textures, wind, breath, static, percussion, ambience
Uses different noise sources filtered and shaped
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class NoiseFilteredTemplate(MethodTemplate):
    """Filtered noise synthesis with multiple noise types."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="subtractive/noise_filtered",
            family="subtractive",
            display_name="Filtered Noise",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="noise_type",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="TYP",
                    tooltip="Noise type (white → pink → brown → gray)",
                    unit="",
                ),
                ParamAxis(
                    name="cutoff_hz",
                    min_val=100.0,
                    max_val=8000.0,
                    default=1500.0,
                    curve="exp",
                    label="CUT",
                    tooltip="Filter cutoff ceiling",
                    unit="Hz",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.0,
                    max_val=0.95,
                    default=0.3,
                    curve="lin",
                    label="RES",
                    tooltip="Filter resonance",
                    unit="",
                ),
                ParamAxis(
                    name="dust_density",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.0,
                    curve="lin",
                    label="DST",
                    tooltip="Velvet-like sparse impulse density",
                    unit="",
                ),
                ParamAxis(
                    name="crackle_amt",
                    min_val=0.0,
                    max_val=0.5,
                    default=0.0,
                    curve="lin",
                    label="CRK",
                    tooltip="Chaotic crackle texture amount",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="darkness",
                    param_weights={
                        "noise_type": 0.6,  # Toward brown
                        "cutoff_hz": -0.8,
                    },
                ),
                MacroControl(
                    name="texture",
                    param_weights={
                        "dust_density": 0.7,
                        "crackle_amt": 0.5,
                        "resonance": 0.3,
                    },
                ),
            ],
            default_tags={"topology": "noise", "exciter": "continuous", "character": "texture"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "noise",
            "exciter": "continuous",
            "family": "subtractive",
            "method": self._definition.method_id,
        }
        
        noise_type = params.get("noise_type", 0.3)
        if noise_type < 0.25:
            tags["character"] = "white"
        elif noise_type < 0.5:
            tags["character"] = "pink"
        elif noise_type < 0.75:
            tags["character"] = "brown"
        else:
            tags["character"] = "gray"
        
        dust = params.get("dust_density", 0.0)
        if dust > 0.5:
            tags["texture"] = "sparse"
        
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
        noise_type_read = axes["noise_type"].sc_read_expr("customBus0", 0)
        cutoff_read = axes["cutoff_hz"].sc_read_expr("customBus1", 1)
        res_read = axes["resonance"].sc_read_expr("customBus2", 2)
        dust_read = axes["dust_density"].sc_read_expr("customBus3", 3)
        crackle_read = axes["crackle_amt"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, noise, dustSig, crackleSig;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var noise_type, cutoff_hz, resonance, dust_density, crackle_amt, rq_scaled;

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
    {noise_type_read}
    {cutoff_read}
    {res_read}
    {dust_read}
    {crackle_read}

    // Calculate RQ from resonance
    rq_scaled = (1.0 - (resonance * 0.9)).max(0.1);

    // === NOISE MIX ===
    // Crossfade between 4 noise types based on noise_type (0-1)
    // 0.0 = white, 0.33 = pink, 0.66 = brown, 1.0 = gray
    noise = SelectX.ar(noise_type * 3, [
        WhiteNoise.ar,
        PinkNoise.ar,
        BrownNoise.ar,
        GrayNoise.ar
    ]);

    // === DUST (velvet-like sparse impulses) ===
    dustSig = Dust2.ar(20 + (dust_density * 500)) * dust_density;
    noise = noise + dustSig;

    // === CRACKLE (chaotic texture) ===
    crackleSig = Crackle.ar(1.5 + (crackle_amt * 0.4)) * crackle_amt * 0.3;
    noise = noise + crackleSig;

    sig = noise;

    // Boost level (noise is naturally quiet after filtering)
    sig = sig * 2;

    // === FILTER ===
    // Use custom cutoff as ceiling, modulated by filter bus
    sig = ~multiFilter.(sig, filterType, filterFreq.min(cutoff_hz), rq * rq_scaled);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.3);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
