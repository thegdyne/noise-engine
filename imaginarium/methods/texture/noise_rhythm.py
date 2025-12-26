"""
imaginarium/methods/texture/noise_rhythm.py
Noise rhythm synthesis - gated noise, percussive textures

Character: Percussive, rhythmic, industrial, textural
Tags: TEX, noise, percussion, rhythmic
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class NoiseRhythmTemplate(MethodTemplate):
    """Gated noise synthesis for rhythmic percussive textures."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="texture/noise_rhythm",
            family="texture",
            display_name="Noise Rhythm",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="tone",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="TON",
                    tooltip="Noise pitch/tone",
                    unit="",
                ),
                ParamAxis(
                    name="snap",
                    min_val=0.001,
                    max_val=0.1,
                    default=0.01,
                    curve="exp",
                    label="SNP",
                    tooltip="Attack snap",
                    unit="s",
                ),
                ParamAxis(
                    name="body",
                    min_val=0.01,
                    max_val=0.5,
                    default=0.1,
                    curve="exp",
                    label="BDY",
                    tooltip="Body decay length",
                    unit="s",
                ),
                ParamAxis(
                    name="color",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="CLR",
                    tooltip="Noise color (dark to bright)",
                    unit="",
                ),
                ParamAxis(
                    name="pitch_env",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="PEN",
                    tooltip="Pitch envelope amount",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="punch",
                    param_weights={
                        "snap": -0.8,  # Shorter = more punch
                        "pitch_env": 0.7,
                    },
                ),
                MacroControl(
                    name="sustain",
                    param_weights={
                        "body": 1.0,
                        "tone": 0.3,
                    },
                ),
            ],
            default_tags={"topology": "noise", "character": "percussive", "role": "accent"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "noise",
            "character": "percussive",
            "role": "accent",
            "family": "texture",
            "method": self._definition.method_id,
        }
        
        body = params.get("body", 0.1)
        if body > 0.3:
            tags["length"] = "long"
        elif body < 0.05:
            tags["length"] = "short"
        
        color = params.get("color", 0.5)
        if color > 0.7:
            tags["brightness"] = "bright"
        elif color < 0.3:
            tags["brightness"] = "dark"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        tone_read = axes["tone"].sc_read_expr("customBus0", 0)
        snap_read = axes["snap"].sc_read_expr("customBus1", 1)
        body_read = axes["body"].sc_read_expr("customBus2", 2)
        color_read = axes["color"].sc_read_expr("customBus3", 3)
        pitch_env_read = axes["pitch_env"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tone, snap, body, color, pitch_env;
    var trig, noise, pitchMod, ampEnv, filterEnv;
    var baseFreq, noiseFiltered;

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
    {tone_read}
    {snap_read}
    {body_read}
    {color_read}
    {pitch_env_read}

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        Impulse.ar(0),  // OFF - single impulse
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // === ENVELOPES ===
    ampEnv = EnvGen.ar(Env.perc(snap, body), trig);
    filterEnv = EnvGen.ar(Env.perc(snap * 0.5, body * 0.5), trig);
    
    // Pitch envelope (drops from high to base)
    pitchMod = EnvGen.ar(Env.perc(0.001, snap * 2), trig).range(1, 1 + (pitch_env * 3));
    
    // === NOISE SOURCE ===
    baseFreq = freq * (0.5 + tone);
    
    // Multi-band noise
    noise = WhiteNoise.ar;
    noise = noise + (PinkNoise.ar * 0.5);
    noise = noise + (BrownNoise.ar * (1 - color) * 0.5);
    
    // === FILTERING ===
    // Resonant filter tuned to frequency
    noiseFiltered = RLPF.ar(noise, (baseFreq * pitchMod).clip(50, 15000), 0.3 - (tone * 0.2));
    
    // Color filter (brightness)
    noiseFiltered = noiseFiltered + HPF.ar(noise * color * 0.3, 3000);
    
    // Body resonance
    noiseFiltered = noiseFiltered + Resonz.ar(noise, baseFreq, 0.1) * tone * 2;
    
    // Filter envelope
    noiseFiltered = LPF.ar(noiseFiltered, (2000 + (filterEnv * 8000) + (color * 6000)).clip(100, 15000));
    
    sig = noiseFiltered * ampEnv;
    
    // Add transient click
    sig = sig + (HPF.ar(WhiteNoise.ar, 5000) * EnvGen.ar(Env.perc(0.0001, 0.002), trig) * 0.3);
    
    // Soft limit
    sig = sig.tanh * 0.8;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.05, 0.25);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
