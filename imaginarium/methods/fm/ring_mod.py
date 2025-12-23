"""
imaginarium/methods/fm/ring_mod.py
Ring modulation synthesis

Character: Metallic, atonal, sci-fi, clangy, dissonant
Multiplies two signals creating sum/difference sidebands
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class RingModTemplate(MethodTemplate):
    """Ring modulation - multiply carrier and modulator."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/ring_mod",
            family="fm",
            display_name="Ring Mod",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="mod_ratio",
                    min_val=0.5,
                    max_val=4.0,
                    default=1.5,
                    curve="lin",
                    label="RAT",
                    tooltip="Modulator frequency ratio",
                    unit="",
                ),
                ParamAxis(
                    name="mod_detune",
                    min_val=0.0,
                    max_val=50.0,
                    default=5.0,
                    curve="lin",
                    label="DET",
                    tooltip="Modulator detune offset",
                    unit="Hz",
                ),
                ParamAxis(
                    name="mix",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="lin",
                    label="MIX",
                    tooltip="Dry/ring-modulated mix",
                    unit="",
                ),
                ParamAxis(
                    name="mod_shape",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.0,
                    curve="lin",
                    label="SHP",
                    tooltip="Modulator waveform (sine → saw)",
                    unit="",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="BRT",
                    tooltip="Output filter brightness",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="dissonance",
                    param_weights={
                        "mod_detune": 0.9,
                        "mod_ratio": 0.5,
                    },
                ),
                MacroControl(
                    name="metallic",
                    param_weights={
                        "mix": 0.8,
                        "brightness": 0.6,
                    },
                ),
            ],
            default_tags={"topology": "ring_mod", "character": "metallic"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "ring_mod",
            "family": "fm",
            "method": self._definition.method_id,
        }
        
        detune = params.get("mod_detune", 5.0)
        mix = params.get("mix", 0.7)
        
        if detune > 20 or mix > 0.8:
            tags["character"] = "atonal"
        elif detune > 5:
            tags["character"] = "metallic"
        else:
            tags["character"] = "harmonic"
        
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
        ratio_read = axes["mod_ratio"].sc_read_expr("customBus0", 0)
        detune_read = axes["mod_detune"].sc_read_expr("customBus1", 1)
        mix_read = axes["mix"].sc_read_expr("customBus2", 2)
        shape_read = axes["mod_shape"].sc_read_expr("customBus3", 3)
        bright_read = axes["brightness"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, carrier, modulator, ringMod, dry;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var mod_ratio, mod_detune, mix, mod_shape, brightness, modFreq;

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
    {ratio_read}
    {detune_read}
    {mix_read}
    {shape_read}
    {bright_read}

    // === CARRIER ===
    // Rich carrier with slight detune for thickness
    carrier = Saw.ar(freq) * 0.7;
    carrier = carrier + (Pulse.ar(freq * 1.001, 0.5) * 0.3);

    // === MODULATOR ===
    // Modulator frequency with ratio and detune
    modFreq = (freq * mod_ratio) + mod_detune;
    
    // Shape: 0 = sine (pure), 1 = saw (harsh)
    modulator = SelectX.ar(mod_shape, [
        SinOsc.ar(modFreq),
        LFSaw.ar(modFreq)
    ]);

    // === RING MODULATION ===
    // Multiply carrier * modulator
    ringMod = carrier * modulator;

    // === MIX ===
    dry = carrier;
    sig = (dry * (1 - mix)) + (ringMod * mix);

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq.min(2000 + (brightness * 6000)), rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.3);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
