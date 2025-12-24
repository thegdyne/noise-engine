"""
imaginarium/methods/subtractive/bright_saw.py
Bright Saw - Classic subtractive synth with emphasis on high harmonics

Characteristics:
- Saw oscillator(s) with optional detune
- Resonant lowpass filter
- High cutoff default for "bright" character
- Optional drive/saturation
"""

from ..base import MethodTemplate, MethodDefinition, ParamAxis, MacroControl


class BrightSawTemplate(MethodTemplate):
    """
    Bright Saw synthesis method.
    
    Good for: Leads, pads, basses with presence
    Brightness range: 0.5-1.0 (biased high)
    Noisiness range: 0.0-0.3 (clean harmonics)
    """
    
    TEMPLATE_VERSION = "1"
    
    @property
    def definition(self) -> MethodDefinition:
        return MethodDefinition(
            method_id="subtractive/bright_saw",
            family="subtractive",
            display_name="Bright Saw",
            template_version=self.TEMPLATE_VERSION,
            param_axes=[
                ParamAxis(
                    name="cutoff_ratio",
                    min_val=0.3,
                    max_val=1.0,
                    default=0.8,
                    curve="lin",
                    label="CUT",
                    tooltip="Filter cutoff as ratio of maximum",
                    unit="",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.1,
                    max_val=0.8,
                    default=0.3,
                    curve="lin",
                    label="RES",
                    tooltip="Filter resonance",
                    unit="",
                ),
                ParamAxis(
                    name="drive",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="lin",
                    label="DRV",
                    tooltip="Pre-filter saturation",
                    unit="",
                ),
                ParamAxis(
                    name="detune",
                    min_val=0.0,
                    max_val=0.03,
                    default=0.005,
                    curve="lin",
                    label="DET",
                    tooltip="Oscillator detune spread",
                    unit="",
                ),
                ParamAxis(
                    name="spread",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="WID",
                    tooltip="Stereo width",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl("TONE", {"cutoff_ratio": 0.8, "resonance": 0.3}),
                MacroControl("EDGE", {"drive": 0.7, "resonance": 0.4}),
                MacroControl("MOTION", {"detune": 0.5, "spread": 0.5}),
            ],
            default_tags={
                "topology": "serial",
                "oscillator": "saw",
                "character": "bright",
            },
        )
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: dict[str, float],
        seed: int,
    ) -> str:
        """Generate SuperCollider SynthDef code."""
        
        # Get axes for sc_read_expr
        axes = {a.name: a for a in self.definition.param_axes}
        
        # Generate custom param read expressions
        cutoff_read = axes["cutoff_ratio"].sc_read_expr("customBus0", 0)
        res_read = axes["resonance"].sc_read_expr("customBus1", 1)
        drive_read = axes["drive"].sc_read_expr("customBus2", 2)
        detune_read = axes["detune"].sc_read_expr("customBus3", 3)
        spread_read = axes["spread"].sc_read_expr("customBus4", 4)
        
        return f'''SynthDef(\\{synthdef_name}, {{
    |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
     filterTypeBus, envEnabledBus, envSourceBus=0,
     clockRateBus, clockTrigBus,
     midiTrigBus=0, slotIndex=0,
     customBus0, customBus1, customBus2, customBus3, customBus4,
     seed={seed}, portamentoBus|

    var freq, filterFreq, rq, attack, decay, filterType, envSource, clockRate, amp, portamento;
    var sig, osc1, osc2, osc3, driven, cutMod;
    var cutoff_ratio, resonance, drive, detune, spread, rq_base;

    // Seed MUST be first before any random UGens
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
    {cutoff_read}
    {res_read}
    {drive_read}
    {detune_read}
    {spread_read}

    // RQ is inverse of resonance for SC filters
    rq_base = 1.0 - (resonance * 0.85);  // Map 0-0.8 resonance to 1.0-0.15 rq

    // === OSCILLATORS ===
    // Main saw
    osc1 = Saw.ar(freq);
    
    // Detuned saws for thickness
    osc2 = Saw.ar(freq * (1 + detune));
    osc3 = Saw.ar(freq * (1 - detune));
    
    // Mix oscillators
    sig = (osc1 * 0.5) + (osc2 * 0.25) + (osc3 * 0.25);

    // === DRIVE (pre-filter saturation) ===
    driven = sig * (1 + (drive * 3));
    sig = driven.tanh * (1 - (drive * 0.3)) + (sig * (drive * 0.3));

    // === FILTER ===
    // Modulate cutoff with ratio
    cutMod = filterFreq * cutoff_ratio;
    
    // Use helper filter with modified RQ
    sig = ~multiFilter.(sig, filterType, cutMod, rq * rq_base);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, spread);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
    
    def get_tags(self, params: dict[str, float]) -> dict[str, str]:
        """Add parameter-dependent tags."""
        tags = super().get_tags(params)
        
        # Characterize based on params
        drive = params.get("drive", 0.2)
        if drive > 0.5:
            tags["saturation"] = "heavy"
        elif drive > 0.2:
            tags["saturation"] = "light"
        else:
            tags["saturation"] = "clean"
        
        detune = params.get("detune", 0.005)
        if detune > 0.015:
            tags["width"] = "wide"
        elif detune > 0.005:
            tags["width"] = "medium"
        else:
            tags["width"] = "tight"
        
        return tags
