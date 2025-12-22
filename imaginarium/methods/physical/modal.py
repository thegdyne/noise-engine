"""
imaginarium/methods/physical/modal.py
Modal synthesis - resonant filter banks

Character: Bells, metals, glass, bars, resonant bodies
Uses Klank UGen for efficient fixed-frequency resonator banks
"""

from dataclasses import dataclass
from typing import Dict, List, Set

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
            template_version=1,
            param_axes=[
                ParamAxis(
                    name="decay_time",
                    min_val=0.5,
                    max_val=10.0,
                    default=3.0,
                    curve="exp",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="linear",
                ),
                ParamAxis(
                    name="inharmonicity",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="linear",
                ),
                ParamAxis(
                    name="density",
                    min_val=0.2,
                    max_val=1.0,
                    default=0.6,
                    curve="linear",
                ),
                ParamAxis(
                    name="strike_brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="linear",
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
        decay = params.get("decay_time", 3.0)
        bright = params.get("brightness", 0.5)
        inharm = params.get("inharmonicity", 0.2)
        density = params.get("density", 0.6)
        strike_bright = params.get("strike_brightness", 0.5)
        
        # Generate mode ratios with inharmonicity
        # Base ratios: 1, 2, 3, 4, 5, 6 (harmonic)
        # Inharmonicity shifts them toward bell-like ratios
        mode_ratios = []
        mode_amps = []
        mode_decays = []
        
        num_modes = int(4 + density * 8)  # 4-12 modes
        
        for i in range(num_modes):
            # Harmonic base
            harmonic = i + 1
            # Add inharmonicity (bell-like stretch)
            ratio = harmonic * (1 + inharm * 0.02 * harmonic * harmonic)
            mode_ratios.append(ratio)
            
            # Higher modes decay faster and are quieter
            amp = 1.0 / (1 + i * 0.5 * (1 + bright))
            mode_amps.append(amp)
            
            # Decay time decreases for higher modes (metallic character)
            mode_decay = decay / (1 + i * 0.15 * (1 - bright * 0.5))
            mode_decays.append(mode_decay)
        
        # Format arrays for SC
        ratios_str = ", ".join(f"{r:.4f}" for r in mode_ratios)
        amps_str = ", ".join(f"{a:.4f}" for a in mode_amps)
        decays_str = ", ".join(f"{d:.4f}" for d in mode_decays)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var exc, sig, trig;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var modeFreqs, modeAmps, modeDecays;

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

    // === TRIGGER ===
    // Standard Noise Engine trigger selection
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // === EXCITER ===
    // Impulse exciter with noise for realism
    exc = WhiteNoise.ar * EnvGen.ar(Env.perc(0.001, 0.01 + ({strike_bright:.4f} * 0.02)), trig);
    exc = exc + (trig * 0.5);  // Add click
    exc = LPF.ar(exc, {2000 + strike_bright * 8000:.1f});

    // === MODAL RESONATOR ===
    // Mode frequencies relative to fundamental
    modeFreqs = [{ratios_str}] * freq;
    modeAmps = [{amps_str}];
    modeDecays = [{decays_str}];

    // DynKlank for dynamic pitch response
    sig = DynKlank.ar(
        `[modeFreqs, modeAmps, modeDecays],
        exc
    );

    // Normalize output
    sig = sig * 0.3;

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.15, 0.25);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  ✓ {synthdef_name} loaded".postln;
'''
    
    def generate_json(self, display_name: str, synthdef_name: str) -> Dict:
        return {
            "name": display_name,
            "synthdef": synthdef_name,
            "custom_params": [],  # Phase 1: no custom params exposed
            "output_trim_db": -6.0,
            "midi_retrig": True,  # Modal sounds need retrigger
            "pitch_target": None,
        }
