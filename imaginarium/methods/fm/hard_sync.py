"""
imaginarium/methods/fm/hard_sync.py
Hard sync oscillator synthesis

Character: Angular, geometric, buzzy, sharp, precise
Hard sync creates complex harmonic spectra by resetting slave oscillator phase
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class HardSyncTemplate(MethodTemplate):
    """Hard sync - angular geometric timbres via oscillator sync."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="fm/hard_sync",
            family="fm",
            display_name="Hard Sync",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="sync_ratio",
                    min_val=1.0,
                    max_val=8.0,
                    default=3.0,
                    curve="lin",
                    label="RAT",
                    tooltip="Slave to master frequency ratio",
                    unit="",
                ),
                ParamAxis(
                    name="sync_sweep",
                    min_val=0.0,
                    max_val=2.0,
                    default=0.5,
                    curve="lin",
                    label="SWP",
                    tooltip="Sync ratio sweep depth",
                    unit="",
                ),
                ParamAxis(
                    name="sweep_rate",
                    min_val=0.1,
                    max_val=8.0,
                    default=0.3,
                    curve="exp",
                    label="SPD",
                    tooltip="Sweep LFO rate",
                    unit="Hz",
                ),
                ParamAxis(
                    name="pulse_mix",
                    min_val=0.0,
                    max_val=0.5,
                    default=0.2,
                    curve="lin",
                    label="PLS",
                    tooltip="Pulse wave mix amount",
                    unit="",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.6,
                    curve="lin",
                    label="BRT",
                    tooltip="Output filter brightness",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="aggression",
                    param_weights={
                        "sync_ratio": 0.8,
                        "brightness": 0.5,
                    },
                ),
                MacroControl(
                    name="movement",
                    param_weights={
                        "sync_sweep": 0.9,
                        "sweep_rate": 0.6,
                    },
                ),
            ],
            default_tags={"topology": "hard_sync", "character": "angular"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "hard_sync",
            "family": "fm",
            "method": self._definition.method_id,
        }
        
        ratio = params.get("sync_ratio", 3.0)
        sweep = params.get("sync_sweep", 0.5)
        
        if ratio > 5:
            tags["character"] = "aggressive"
        elif ratio > 2.5:
            tags["character"] = "angular"
        else:
            tags["character"] = "smooth"
        
        if sweep > 1.0:
            tags["movement"] = "sweeping"
        else:
            tags["movement"] = "static"
        
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
        ratio_read = axes["sync_ratio"].sc_read_expr("customBus0", 0)
        sweep_read = axes["sync_sweep"].sc_read_expr("customBus1", 1)
        rate_read = axes["sweep_rate"].sc_read_expr("customBus2", 2)
        pulse_read = axes["pulse_mix"].sc_read_expr("customBus3", 3)
        bright_read = axes["brightness"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, syncOsc, pulseOsc, slaveFreq, ratioMod;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var sync_ratio, sync_sweep, sweep_rate, pulse_mix, brightness;

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
    {ratio_read}
    {sweep_read}
    {rate_read}
    {pulse_read}
    {bright_read}

    // === SYNC OSCILLATOR ===
    // LFO modulates sync ratio for movement
    ratioMod = LFTri.kr(sweep_rate).range(1 - sync_sweep, 1 + sync_sweep);
    slaveFreq = freq * sync_ratio * ratioMod;
    
    // Hard sync saw - slave resets at master frequency
    syncOsc = SyncSaw.ar(freq, slaveFreq);
    
    // Add pulse for extra edge
    pulseOsc = Pulse.ar(freq, 0.5);
    
    // Mix
    sig = (syncOsc * (1 - pulse_mix)) + (pulseOsc * pulse_mix);

    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq.min(1500 + (brightness * 5500)), rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.15, 0.25);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
