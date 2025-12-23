"""
imaginarium/methods/subtractive/dark_pulse.py
Dark pulse wave subtractive synthesizer

Character: Dark, hollow, PWM movement
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class DarkPulseTemplate(MethodTemplate):
    """Dark pulse wave with PWM and low-pass filtering."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="subtractive/dark_pulse",
            family="subtractive",
            display_name="Dark Pulse",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="pulse_width",
                    min_val=0.1,
                    max_val=0.9,
                    default=0.5,
                    curve="lin",
                    label="WID",
                    tooltip="Base pulse width",
                    unit="",
                ),
                ParamAxis(
                    name="pwm_depth",
                    min_val=0.0,
                    max_val=0.4,
                    default=0.1,
                    curve="lin",
                    label="PWM",
                    tooltip="Pulse width modulation depth",
                    unit="",
                ),
                ParamAxis(
                    name="pwm_rate",
                    min_val=0.1,
                    max_val=4.0,
                    default=0.5,
                    curve="exp",
                    label="RAT",
                    tooltip="PWM LFO rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="cutoff_hz",
                    min_val=100.0,
                    max_val=2000.0,
                    default=800.0,
                    curve="exp",
                    label="CUT",
                    tooltip="Filter cutoff ceiling",
                    unit="Hz",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.0,
                    max_val=0.8,
                    default=0.2,
                    curve="lin",
                    label="RES",
                    tooltip="Filter resonance",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="darkness",
                    param_weights={
                        "cutoff_hz": -1.0,
                        "resonance": 0.5,
                    },
                ),
                MacroControl(
                    name="movement",
                    param_weights={
                        "pwm_depth": 1.0,
                        "pwm_rate": 0.8,
                    },
                ),
            ],
            default_tags={"topology": "serial", "oscillator": "pulse", "character": "dark"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "serial",
            "oscillator": "pulse",
            "character": "dark",
            "family": "subtractive",
            "method": self._definition.method_id,
        }
        
        cutoff = params.get("cutoff_hz", 800)
        if cutoff < 400:
            tags["brightness"] = "very_dark"
        elif cutoff < 800:
            tags["brightness"] = "dark"
        else:
            tags["brightness"] = "medium"
        
        pwm = params.get("pwm_depth", 0.1)
        if pwm > 0.2:
            tags["modulation"] = "pwm"
        
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
        pw_read = axes["pulse_width"].sc_read_expr("customBus0", 0)
        pwm_depth_read = axes["pwm_depth"].sc_read_expr("customBus1", 1)
        pwm_rate_read = axes["pwm_rate"].sc_read_expr("customBus2", 2)
        cutoff_read = axes["cutoff_hz"].sc_read_expr("customBus3", 3)
        res_read = axes["resonance"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, width, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var pulse_width, pwm_depth, pwm_rate, cutoff_hz, resonance, rq_mult;

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
    {pw_read}
    {pwm_depth_read}
    {pwm_rate_read}
    {cutoff_read}
    {res_read}

    // Calculate RQ from resonance (higher res = lower rq)
    rq_mult = (1.0 - (resonance * 0.8)).max(0.2);

    // === PWM PULSE OSCILLATOR ===
    width = pulse_width + (SinOsc.kr(pwm_rate) * pwm_depth);
    width = width.clip(0.1, 0.9);
    sig = Pulse.ar(freq, width);

    // === FILTER ===
    // Use custom cutoff as ceiling, modulated by filter bus
    sig = ~multiFilter.(sig, filterType, filterFreq.min(cutoff_hz), rq * rq_mult);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.15, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
