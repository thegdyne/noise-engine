"""
imaginarium/methods/fm/feedback_fm.py
Feedback FM synthesis - self-modulating operator

Character: Gritty, aggressive, chaotic, industrial
Single operator with feedback creates rich harmonics to noise
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class FeedbackFMTemplate(MethodTemplate):
    """Feedback FM synthesis - self-modulating oscillator."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/feedback_fm",
            family="fm",
            display_name="Feedback FM",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="feedback",
                    min_val=0.0,
                    max_val=1.5,
                    default=0.5,
                    curve="lin",
                    label="FBK",
                    tooltip="Self-modulation feedback amount",
                    unit="",
                ),
                ParamAxis(
                    name="fb_mod_rate",
                    min_val=0.1,
                    max_val=8.0,
                    default=0.5,
                    curve="exp",
                    label="RAT",
                    tooltip="Feedback modulation LFO rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="fb_mod_depth",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="DEP",
                    tooltip="Feedback modulation depth",
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
                ParamAxis(
                    name="drive",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="lin",
                    label="DRV",
                    tooltip="Waveshaping drive amount",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="chaos",
                    param_weights={
                        "feedback": 0.9,
                        "fb_mod_depth": 0.6,
                        "drive": 0.4,
                    },
                ),
                MacroControl(
                    name="movement",
                    param_weights={
                        "fb_mod_rate": 0.8,
                        "fb_mod_depth": 0.5,
                    },
                ),
            ],
            default_tags={"topology": "fm", "character": "aggressive"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "fm",
            "family": "fm",
            "method": self._definition.method_id,
        }
        
        fb = params.get("feedback", 0.5)
        if fb > 1.0:
            tags["character"] = "chaotic"
        elif fb > 0.6:
            tags["character"] = "aggressive"
        elif fb > 0.3:
            tags["character"] = "gritty"
        else:
            tags["character"] = "warm"
        
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
        fb_read = axes["feedback"].sc_read_expr("customBus0", 0)
        rate_read = axes["fb_mod_rate"].sc_read_expr("customBus1", 1)
        depth_read = axes["fb_mod_depth"].sc_read_expr("customBus2", 2)
        bright_read = axes["brightness"].sc_read_expr("customBus3", 3)
        drive_read = axes["drive"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, fbMod, fbAmount;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var feedback, fb_mod_rate, fb_mod_depth, brightness, drive;

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
    {fb_read}
    {rate_read}
    {depth_read}
    {bright_read}
    {drive_read}

    // === FEEDBACK FM ===
    // Modulate feedback amount for movement
    fbMod = SinOsc.kr(fb_mod_rate).range(1 - fb_mod_depth, 1);
    fbAmount = feedback * fbMod;
    
    // Self-modulating FM oscillator
    // SinOscFB has built-in feedback path
    sig = SinOscFB.ar(freq, fbAmount);
    
    // Add slight detuned copy for thickness
    sig = sig + (SinOscFB.ar(freq * 1.003, fbAmount * 0.9) * 0.3);
    sig = sig * 0.7;  // Normalize mix

    // === DRIVE (waveshaping) ===
    sig = (sig * (1 + (drive * 4))).tanh;
    sig = sig * (1 - (drive * 0.3));  // Compensate gain

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq.min(1000 + (brightness * 8000)), rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
