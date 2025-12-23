"""
imaginarium/methods/subtractive/wavefold.py
Wavefolding synthesis - West Coast style harmonic generation

Character: Metallic, complex harmonics, evolving timbres
Tags: NL, nonlinear, West Coast
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class WavefoldTemplate(MethodTemplate):
    """Wavefolding synthesis with multiple folding stages."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="subtractive/wavefold",
            family="subtractive",
            display_name="Wavefold",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="fold_amount",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.4,
                    curve="lin",
                    label="FLD",
                    tooltip="Wavefolding intensity",
                    unit="",
                ),
                ParamAxis(
                    name="symmetry",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="SYM",
                    tooltip="Fold symmetry (0=asym, 1=sym)",
                    unit="",
                ),
                ParamAxis(
                    name="drive",
                    min_val=1.0,
                    max_val=8.0,
                    default=2.0,
                    curve="exp",
                    label="DRV",
                    tooltip="Input gain before folding",
                    unit="x",
                ),
                ParamAxis(
                    name="stages",
                    min_val=1.0,
                    max_val=4.0,
                    default=2.0,
                    curve="lin",
                    label="STG",
                    tooltip="Number of fold stages",
                    unit="",
                ),
                ParamAxis(
                    name="mix",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.6,
                    curve="lin",
                    label="MIX",
                    tooltip="Dry/wet mix",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="intensity",
                    param_weights={
                        "fold_amount": 1.0,
                        "drive": 0.7,
                        "stages": 0.5,
                    },
                ),
                MacroControl(
                    name="character",
                    param_weights={
                        "symmetry": 1.0,
                        "mix": 0.3,
                    },
                ),
            ],
            default_tags={"topology": "nonlinear", "character": "metallic"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "nonlinear",
            "character": "metallic",
            "family": "subtractive",
            "method": self._definition.method_id,
        }
        
        fold = params.get("fold_amount", 0.4)
        if fold > 0.7:
            tags["intensity"] = "aggressive"
        elif fold < 0.2:
            tags["intensity"] = "subtle"
        else:
            tags["intensity"] = "moderate"
        
        sym = params.get("symmetry", 0.5)
        if sym > 0.7:
            tags["harmonics"] = "even"
        elif sym < 0.3:
            tags["harmonics"] = "odd"
        else:
            tags["harmonics"] = "mixed"
        
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
        fold_read = axes["fold_amount"].sc_read_expr("customBus0", 0)
        symmetry_read = axes["symmetry"].sc_read_expr("customBus1", 1)
        drive_read = axes["drive"].sc_read_expr("customBus2", 2)
        stages_read = axes["stages"].sc_read_expr("customBus3", 3)
        mix_read = axes["mix"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, dry, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var fold_amount, symmetry, drive, stages, mix;
    var folded, foldGain, offset;

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
    {fold_read}
    {symmetry_read}
    {drive_read}
    {stages_read}
    {mix_read}

    // === SOURCE OSCILLATOR ===
    // Start with a simple waveform to fold
    sig = SinOsc.ar(freq);
    // Add slight triangle component for asymmetry
    sig = sig + (LFTri.ar(freq) * (1 - symmetry) * 0.3);
    
    // Store dry signal
    dry = sig;

    // === WAVEFOLDING ===
    // Apply drive
    foldGain = drive * (1 + (fold_amount * 4));
    sig = sig * foldGain;
    
    // Asymmetry offset
    offset = (1 - symmetry) * 0.5 * fold_amount;
    sig = sig + offset;
    
    // Fold function - using sine waveshaping for smooth folds
    // Stage 1 (always active)
    folded = sig.fold(-1, 1);
    
    // Stage 2
    folded = Select.ar(stages > 1.5, [
        folded,
        (folded * 1.5).fold(-1, 1)
    ]);
    
    // Stage 3
    folded = Select.ar(stages > 2.5, [
        folded,
        (folded * 1.3).fold(-1, 1)
    ]);
    
    // Stage 4
    folded = Select.ar(stages > 3.5, [
        folded,
        (folded * 1.2).fold(-1, 1)
    ]);
    
    // Normalize output
    sig = folded * 0.5;
    
    // === DRY/WET MIX ===
    sig = (dry * (1 - mix)) + (sig * mix);
    
    // Add subtle stereo width from fold modulation
    sig = sig + (SinOsc.ar(freq * 2.01) * fold_amount * 0.1);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.15);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
