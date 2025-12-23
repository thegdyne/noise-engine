"""
imaginarium/methods/texture/chaos_osc.py
Chaotic oscillator synthesis - Lorenz/Henon-inspired unpredictable textures

Character: Unpredictable, evolving, organic, alive
Tags: STOCH, chaos, nonlinear, evolving
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class ChaosOscTemplate(MethodTemplate):
    """Chaotic oscillator synthesis using nonlinear dynamics."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="texture/chaos_osc",
            family="texture",
            display_name="Chaos Osc",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="chaos",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="CHS",
                    tooltip="Chaos amount (order to chaos)",
                    unit="",
                ),
                ParamAxis(
                    name="rate",
                    min_val=0.1,
                    max_val=20.0,
                    default=2.0,
                    curve="exp",
                    label="RAT",
                    tooltip="Base oscillation rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="coupling",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.4,
                    curve="lin",
                    label="CPL",
                    tooltip="Oscillator coupling strength",
                    unit="",
                ),
                ParamAxis(
                    name="tonal",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="TON",
                    tooltip="Tonal vs noise character",
                    unit="",
                ),
                ParamAxis(
                    name="damping",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="DMP",
                    tooltip="High frequency damping",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="wildness",
                    param_weights={
                        "chaos": 1.0,
                        "coupling": 0.7,
                    },
                ),
                MacroControl(
                    name="stability",
                    param_weights={
                        "tonal": 1.0,
                        "damping": 0.6,
                    },
                ),
            ],
            default_tags={"topology": "chaos", "character": "unpredictable"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "chaos",
            "character": "unpredictable",
            "family": "texture",
            "method": self._definition.method_id,
        }
        
        chaos = params.get("chaos", 0.5)
        if chaos > 0.7:
            tags["stability"] = "chaotic"
        elif chaos < 0.3:
            tags["stability"] = "ordered"
        else:
            tags["stability"] = "edge"
        
        tonal = params.get("tonal", 0.3)
        if tonal > 0.6:
            tags["tonality"] = "tonal"
        else:
            tags["tonality"] = "noisy"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        chaos_read = axes["chaos"].sc_read_expr("customBus0", 0)
        rate_read = axes["rate"].sc_read_expr("customBus1", 1)
        coupling_read = axes["coupling"].sc_read_expr("customBus2", 2)
        tonal_read = axes["tonal"].sc_read_expr("customBus3", 3)
        damping_read = axes["damping"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var chaos, rate, coupling, tonal, damping;
    var chaosL, chaosR, lorenz, henon, crackle;
    var tonalOsc, modulated, dampFreq;

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
    {chaos_read}
    {rate_read}
    {coupling_read}
    {tonal_read}
    {damping_read}

    // === CHAOTIC OSCILLATORS ===
    // Lorenz-like using coupled feedback
    lorenz = SinOscFB.ar(rate * 10, chaos * 1.5);
    lorenz = lorenz + (SinOscFB.ar(rate * 10.1, chaos * 1.4) * coupling);
    
    // Henon-like using Crackle
    crackle = Crackle.ar(1.5 + (chaos * 0.49));  // 1.5-1.99 range
    
    // Standard chaotic oscillator
    henon = StandardN.ar(rate * 100, chaos.linlin(0, 1, 0.7, 1.4));
    
    // Mix chaotic sources
    chaosL = (lorenz * 0.4) + (crackle * 0.3) + (henon * 0.3);
    chaosR = (lorenz * 0.35) + (crackle * 0.35) + (henon * 0.3);
    
    // Add coupling between L/R
    chaosL = chaosL + (chaosR * coupling * 0.3);
    chaosR = chaosR + (chaosL * coupling * 0.3);
    
    // === TONAL COMPONENT ===
    // Modulate oscillator with chaos
    modulated = SinOsc.ar(freq * (1 + (chaosL * 0.1 * chaos)));
    modulated = modulated + (SinOsc.ar(freq * 2 * (1 + (chaosR * 0.05 * chaos))) * 0.3);
    
    tonalOsc = modulated * tonal;
    
    // === MIX ===
    sig = [chaosL, chaosR] * (1 - tonal) + [tonalOsc, tonalOsc];
    
    // === DAMPING ===
    dampFreq = (1 - damping).linexp(0, 1, 500, 16000);
    sig = LPF.ar(sig, dampFreq);
    
    // Soft limiting
    sig = sig.tanh * 0.5;

    // === OUTPUT CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
