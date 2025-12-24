"""
imaginarium/methods/texture/bitcrush.py
Bitcrush synthesis - lo-fi, retro, digital destruction

Character: Lo-fi, retro, gritty, 8-bit
Tags: TEX, lofi, digital, bitcrush
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class BitcrushTemplate(MethodTemplate):
    """Bitcrusher synthesis for lo-fi digital sounds."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="texture/bitcrush",
            family="texture",
            display_name="Bitcrush",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="bits",
                    min_val=2.0,
                    max_val=16.0,
                    default=8.0,
                    curve="lin",
                    label="BIT",
                    tooltip="Bit depth",
                    unit="bits",
                ),
                ParamAxis(
                    name="sample_rate",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="SRT",
                    tooltip="Sample rate reduction",
                    unit="",
                ),
                ParamAxis(
                    name="source",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="SRC",
                    tooltip="Noise vs tone source",
                    unit="",
                ),
                ParamAxis(
                    name="fold",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.0,
                    curve="lin",
                    label="FLD",
                    tooltip="Pre-crush wavefold",
                    unit="",
                ),
                ParamAxis(
                    name="drive",
                    min_val=1.0,
                    max_val=4.0,
                    default=1.5,
                    curve="exp",
                    label="DRV",
                    tooltip="Input drive",
                    unit="x",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="crunch",
                    param_weights={
                        "bits": -1.0,  # Lower bits = more crunch
                        "sample_rate": 1.0,
                    },
                ),
                MacroControl(
                    name="aggression",
                    param_weights={
                        "drive": 1.0,
                        "fold": 0.7,
                    },
                ),
            ],
            default_tags={"topology": "bitcrush", "character": "lofi"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "bitcrush",
            "character": "lofi",
            "family": "texture",
            "method": self._definition.method_id,
        }
        
        bits = params.get("bits", 8.0)
        if bits <= 4:
            tags["quality"] = "destroyed"
        elif bits <= 8:
            tags["quality"] = "retro"
        else:
            tags["quality"] = "mild"
        
        source = params.get("source", 0.5)
        if source > 0.7:
            tags["tonality"] = "tonal"
        elif source < 0.3:
            tags["tonality"] = "noisy"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        bits_read = axes["bits"].sc_read_expr("customBus0", 0)
        sample_rate_read = axes["sample_rate"].sc_read_expr("customBus1", 1)
        source_read = axes["source"].sc_read_expr("customBus2", 2)
        fold_read = axes["fold"].sc_read_expr("customBus3", 3)
        drive_read = axes["drive"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bits, sample_rate, source, fold, drive;
    var tone, noise, crushed, downsampleRate, bitDepth;

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
    {bits_read}
    {sample_rate_read}
    {source_read}
    {fold_read}
    {drive_read}

    // === SOURCE ===
    // Tonal component
    tone = Saw.ar(freq) * 0.5;
    tone = tone + (Pulse.ar(freq * 0.5, 0.3) * 0.3);
    tone = tone + (SinOsc.ar(freq) * 0.2);
    
    // Noise component
    noise = PinkNoise.ar;
    noise = Resonz.ar(noise, freq, 0.3) * 3;
    noise = noise + (WhiteNoise.ar * 0.3);
    
    // Mix source
    sig = (tone * source) + (noise * (1 - source));
    
    // === DRIVE ===
    sig = sig * drive;
    
    // === WAVEFOLD (pre-crush) ===
    sig = sig + (sig.fold(-1, 1) * fold * 2);
    sig = sig / (1 + fold);
    
    // === BITCRUSH ===
    // Bit reduction
    bitDepth = 2.pow(bits.round);
    sig = (sig * bitDepth).round / bitDepth;
    
    // Sample rate reduction
    downsampleRate = sample_rate.linexp(0, 1, 48000, 1000);
    sig = Latch.ar(sig, Impulse.ar(downsampleRate));
    
    // === POST-PROCESSING ===
    // Soft clip the aliasing
    sig = sig.tanh;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
