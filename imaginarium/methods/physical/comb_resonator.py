"""
imaginarium/methods/physical/comb_resonator.py
Comb filter resonator - metallic, flanged, pitched delays

Character: Metallic, flanged, ringy, ethereal
Tags: MODEL, comb, resonator, metallic
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class CombResonatorTemplate(MethodTemplate):
    """Comb filter resonator for metallic/flanged sounds."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="physical/comb_resonator",
            family="physical",
            display_name="Comb Resonator",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="feedback",
                    min_val=0.01,
                    max_val=0.99,
                    default=0.8,
                    curve="lin",
                    label="FBK",
                    tooltip="Comb feedback amount",
                    unit="",
                ),
                ParamAxis(
                    name="damping",
                    min_val=0.01,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="DMP",
                    tooltip="High frequency damping",
                    unit="",
                ),
                ParamAxis(
                    name="detune",
                    min_val=0.01,
                    max_val=1.0,
                    default=0.2,
                    curve="lin",
                    label="DTN",
                    tooltip="Comb pitch spread",
                    unit="",
                ),
                ParamAxis(
                    name="excite",
                    min_val=0.01,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="EXC",
                    tooltip="Exciter brightness",
                    unit="",
                ),
                ParamAxis(
                    name="mod_rate",
                    min_val=0.01,
                    max_val=5.0,
                    default=0.5,
                    curve="exp",
                    label="MOD",
                    tooltip="Delay time modulation",
                    unit="Hz",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="resonance",
                    param_weights={
                        "feedback": 1.0,
                        "damping": -0.5,
                    },
                ),
                MacroControl(
                    name="movement",
                    param_weights={
                        "mod_rate": 1.0,
                        "detune": 0.6,
                    },
                ),
            ],
            default_tags={"topology": "comb", "character": "metallic"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "comb",
            "character": "metallic",
            "family": "physical",
            "method": self._definition.method_id,
        }
        
        feedback = params.get("feedback", 0.8)
        if feedback > 0.9:
            tags["sustain"] = "infinite"
        elif feedback < 0.5:
            tags["sustain"] = "short"
        
        mod_rate = params.get("mod_rate", 0.5)
        if mod_rate > 2.0:
            tags["motion"] = "flanged"
        elif mod_rate < 0.1:
            tags["motion"] = "static"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        feedback_read = axes["feedback"].sc_read_expr("customBus0", 0)
        damping_read = axes["damping"].sc_read_expr("customBus1", 1)
        detune_read = axes["detune"].sc_read_expr("customBus2", 2)
        excite_read = axes["excite"].sc_read_expr("customBus3", 3)
        mod_rate_read = axes["mod_rate"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var feedback, damping, detune, excite, modRate;
    var exciter, delayTime, delayMod, dampFreq;
    var comb1, comb2, comb3, comb4;

    // Seed for determinism
    RandSeed.ir(1, seed);

    // Read standard params
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
    {feedback_read}
    {damping_read}
    {detune_read}
    {excite_read}
    {mod_rate_read}

    // === EXCITER ===
    exciter = PinkNoise.ar * 0.5;
    exciter = exciter + (Impulse.ar(0) * 0.5);
    exciter = HPF.ar(exciter, 100 + (excite * 4000));
    exciter = LPF.ar(exciter, 2000 + (excite * 10000));
    
    // Base delay time from frequency
    delayTime = 1 / freq;
    
    // Modulation
    delayMod = SinOsc.kr(modRate).range(0.98, 1.02);
    
    // Damping frequency
    dampFreq = (1 - damping).linexp(0, 1, 500, 15000);
    
    // === COMB FILTERS (4 parallel, slightly detuned) ===
    comb1 = CombL.ar(exciter, 0.1, (delayTime * delayMod).clip(0.0001, 0.1), feedback * 4);
    comb1 = LPF.ar(comb1, dampFreq);
    
    comb2 = CombL.ar(exciter, 0.1, (delayTime * (1 + (detune * 0.02)) * delayMod).clip(0.0001, 0.1), feedback * 4);
    comb2 = LPF.ar(comb2, dampFreq * 0.9);
    
    comb3 = CombL.ar(exciter, 0.1, (delayTime * (1 - (detune * 0.015)) * delayMod).clip(0.0001, 0.1), feedback * 4);
    comb3 = LPF.ar(comb3, dampFreq * 1.1);
    
    comb4 = CombL.ar(exciter, 0.1, (delayTime * (1 + (detune * 0.01)) * delayMod).clip(0.0001, 0.1), feedback * 4);
    comb4 = LPF.ar(comb4, dampFreq);
    
    // Mix with stereo spread
    sig = [
        (comb1 + comb3) * 0.5,
        (comb2 + comb4) * 0.5
    ];
    
    // Add exciter for attack
    sig = sig + (exciter * 0.3);
    
    // DC blocking
    sig = LeakDC.ar(sig);
    
    // Soft limit
    sig = sig.tanh * 0.7;

    // === OUTPUT CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
