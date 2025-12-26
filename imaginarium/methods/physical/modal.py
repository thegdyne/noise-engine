"""
imaginarium/methods/physical/modal.py
Modal synthesis - resonant filter banks

Character: Bells, metals, glass, bars, resonant bodies
Uses DynKlank UGen for dynamic resonator banks
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class ModalTemplate(MethodTemplate):
    """Modal synthesis using resonant filter banks."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="physical/modal",
            family="physical",
            display_name="Modal Resonator",
            template_version="2",  # Bumped for dynamic params
            param_axes=[
                ParamAxis(
                    name="decay_time",
                    min_val=0.5,
                    max_val=10.0,
                    default=3.0,
                    curve="exp",
                    label="DEC",
                    tooltip="Mode decay time",
                    unit="s",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="BRT",
                    tooltip="High mode emphasis",
                    unit="",
                ),
                ParamAxis(
                    name="inharmonicity",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="lin",
                    label="INH",
                    tooltip="Modal frequency stretch",
                    unit="",
                ),
                ParamAxis(
                    name="density",
                    min_val=0.2,
                    max_val=1.0,
                    default=0.6,
                    curve="lin",
                    label="DNS",
                    tooltip="Mode amplitude density",
                    unit="",
                ),
                ParamAxis(
                    name="strike_brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="STK",
                    tooltip="Strike exciter brightness",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="material",
                    param_weights={
                        "decay_time": 0.7,
                        "inharmonicity": 0.8,
                        "brightness": 0.5,
                    },
                ),
                MacroControl(
                    name="size",
                    param_weights={
                        "density": -0.6,
                        "brightness": -0.4,
                    },
                ),
            ],
            default_tags={"topology": "physical", "exciter": "impulse", "character": "resonant"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "physical",
            "exciter": "impulse",
            "family": "physical",
            "method": self._definition.method_id,
        }
        
        decay = params.get("decay_time", 3.0)
        if decay > 6:
            tags["sustain"] = "long"
        elif decay < 1.5:
            tags["sustain"] = "short"
        else:
            tags["sustain"] = "medium"
        
        inharm = params.get("inharmonicity", 0.2)
        if inharm > 0.6:
            tags["character"] = "metallic"
        elif inharm < 0.15:
            tags["character"] = "harmonic"
        else:
            tags["character"] = "bell"
        
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
        decay_read = axes["decay_time"].sc_read_expr("customBus0", 0)
        bright_read = axes["brightness"].sc_read_expr("customBus1", 1)
        inharm_read = axes["inharmonicity"].sc_read_expr("customBus2", 2)
        density_read = axes["density"].sc_read_expr("customBus3", 3)
        strike_read = axes["strike_brightness"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var exc, sig, trig;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var decay_time, brightness, inharmonicity, density, strike_brightness;
    var modeRatios, modeAmps, modeDecays, modeFreqs;

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
    {decay_read}
    {bright_read}
    {inharm_read}
    {density_read}
    {strike_read}

    // === TRIGGER ===
    // Standard Noise Engine trigger selection
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // === EXCITER ===
    // Impulse exciter with noise for realism
    exc = WhiteNoise.ar * EnvGen.ar(Env.perc(0.001, 0.01 + (strike_brightness * 0.02)), trig);
    exc = exc + (trig * 0.5);  // Add click
    exc = LPF.ar(exc, 2000 + (strike_brightness * 8000));

    // === MODAL RESONATOR ===
    // Fixed 8 modes with dynamic parameters
    // Base ratios: 1, 2, 3, 4, 5, 6, 7, 8 with inharmonic stretch
    modeRatios = (1..8).collect {{ |i|
        i * (1 + (inharmonicity * 0.02 * i * i))
    }};
    modeFreqs = modeRatios * freq;
    
    // Amplitudes: higher modes quieter, brightness boosts highs
    modeAmps = (1..8).collect {{ |i|
        var baseAmp = 1.0 / (1 + ((i - 1) * 0.5));
        baseAmp * (1 + (brightness * (i - 1) * 0.1)) * density
    }};
    
    // Decay times: higher modes decay faster
    modeDecays = (1..8).collect {{ |i|
        decay_time / (1 + ((i - 1) * 0.15 * (1 - (brightness * 0.5))))
    }};

    // DynKlank for dynamic pitch/parameter response
    sig = DynKlank.ar(
        `[modeFreqs, modeAmps, modeDecays],
        exc
    );

    // Normalize output
    sig = sig * 0.25;

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.15, 0.25);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
