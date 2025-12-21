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
                ParamAxis("cutoff_ratio", 0.3, 1.0, 0.8, "lin"),   # Cutoff as ratio of max
                ParamAxis("resonance", 0.1, 0.8, 0.3, "lin"),      # Filter Q
                ParamAxis("drive", 0.0, 1.0, 0.2, "lin"),          # Pre-filter saturation
                ParamAxis("detune", 0.0, 0.03, 0.005, "lin"),      # Oscillator detune
                ParamAxis("spread", 0.0, 1.0, 0.3, "lin"),         # Stereo width
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
        
        # Extract params with defaults
        cutoff_ratio = params.get("cutoff_ratio", 0.8)
        resonance = params.get("resonance", 0.3)
        drive = params.get("drive", 0.2)
        detune = params.get("detune", 0.005)
        spread = params.get("spread", 0.3)
        
        # RQ is inverse of resonance for SC filters
        rq_base = 1.0 - (resonance * 0.85)  # Map 0-0.8 resonance to 1.0-0.15 rq
        
        return f'''SynthDef(\\{synthdef_name}, {{
    |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
     filterTypeBus, envEnabledBus, envSourceBus=0,
     clockRateBus, clockTrigBus,
     midiTrigBus=0, slotIndex=0,
     customBus0, customBus1, customBus2, customBus3, customBus4,
     seed=0|

    var freq, filterFreq, rq, attack, decay, filterType, envSource, clockRate, amp;
    var sig, osc1, osc2, osc3, driven, cutMod;

    // Seed MUST be first before any random UGens
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

    // === OSCILLATORS ===
    // Main saw
    osc1 = Saw.ar(freq);
    
    // Detuned saws for thickness (detune amount baked in)
    osc2 = Saw.ar(freq * (1 + {detune:.6f}));
    osc3 = Saw.ar(freq * (1 - {detune:.6f}));
    
    // Mix oscillators
    sig = (osc1 * 0.5) + (osc2 * 0.25) + (osc3 * 0.25);

    // === DRIVE (pre-filter saturation) ===
    driven = sig * (1 + ({drive:.4f} * 3));
    sig = driven.tanh * (1 - ({drive:.4f} * 0.3)) + (sig * ({drive:.4f} * 0.3));

    // === FILTER ===
    // Modulate cutoff with baked-in ratio
    cutMod = filterFreq * {cutoff_ratio:.4f};
    
    // Use helper filter with modified RQ
    sig = ~multiFilter.(sig, filterType, cutMod, rq * {rq_base:.4f});

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, {spread:.4f});
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  ✓ {synthdef_name} loaded".postln;
'''
    
    def generate_json(
        self,
        display_name: str,
        synthdef_name: str,
    ) -> dict:
        """Generate generator JSON config."""
        return {
            "name": display_name,
            "synthdef": synthdef_name,
            "custom_params": [],  # Phase 1: no custom params exposed
            "output_trim_db": -6.0,
            "midi_retrig": False,
            "pitch_target": None,
        }
    
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
