"""
imaginarium/methods/physical/formant.py
Formant synthesis - vowel/vocal resonances

Character: Breathy, vocal, choir-like, organic, human
Uses multiple bandpass filters at formant frequencies
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class FormantTemplate(MethodTemplate):
    """Formant synthesis - vocal tract resonances."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="physical/formant",
            family="physical",
            display_name="Formant Voice",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="vowel",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="VOW",
                    tooltip="Vowel morph (A→E→I→O→U)",
                    unit="",
                ),
                ParamAxis(
                    name="breathiness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="BRH",
                    tooltip="Breath noise amount",
                    unit="",
                ),
                ParamAxis(
                    name="formant_shift",
                    min_val=0.5,
                    max_val=2.0,
                    default=1.0,
                    curve="lin",
                    label="SHF",
                    tooltip="Formant frequency shift",
                    unit="",
                ),
                ParamAxis(
                    name="formant_width",
                    min_val=0.5,
                    max_val=2.0,
                    default=1.0,
                    curve="lin",
                    label="WID",
                    tooltip="Formant bandwidth",
                    unit="",
                ),
                ParamAxis(
                    name="vibrato_depth",
                    min_val=0.0,
                    max_val=0.02,
                    default=0.005,
                    curve="lin",
                    label="VIB",
                    tooltip="Vibrato depth",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="openness",
                    param_weights={
                        "vowel": 0.8,
                        "formant_shift": 0.4,
                    },
                ),
                MacroControl(
                    name="airiness",
                    param_weights={
                        "breathiness": 0.9,
                        "formant_width": 0.5,
                    },
                ),
            ],
            default_tags={"topology": "formant", "exciter": "pulse", "character": "vocal"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "formant",
            "exciter": "pulse",
            "family": "physical",
            "method": self._definition.method_id,
        }
        
        breath = params.get("breathiness", 0.3)
        if breath > 0.6:
            tags["character"] = "breathy"
        elif breath < 0.2:
            tags["character"] = "clear"
        else:
            tags["character"] = "vocal"
        
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
        vowel_read = axes["vowel"].sc_read_expr("customBus0", 0)
        breath_read = axes["breathiness"].sc_read_expr("customBus1", 1)
        shift_read = axes["formant_shift"].sc_read_expr("customBus2", 2)
        width_read = axes["formant_width"].sc_read_expr("customBus3", 3)
        vib_read = axes["vibrato_depth"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, source, noise, vibrato, formants;
    var f1, f2, f3, bw;
    var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var vowel, breathiness, formant_shift, formant_width, vibrato_depth;

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
    {vowel_read}
    {breath_read}
    {shift_read}
    {width_read}
    {vib_read}

    // === VIBRATO ===
    vibrato = SinOsc.kr(5.5).range(1 - vibrato_depth, 1 + vibrato_depth);
    freq = freq * vibrato;

    // === SOURCE (glottal pulse + noise) ===
    // Pulse train as glottal source
    source = Pulse.ar(freq, 0.3) * (1 - breathiness);
    
    // Add breathiness (noise component)
    noise = PinkNoise.ar * breathiness;
    source = source + noise;

    // === FORMANT FILTERS ===
    // Formant frequencies with shift
    // Interpolate: A(0) -> E(0.25) -> I(0.5) -> O(0.75) -> U(1.0)
    f1 = Select.kr((vowel * 4).floor.clip(0, 4), [800, 400, 300, 500, 350]);
    f1 = f1 + ((vowel * 4).frac * Select.kr((vowel * 4).floor.clip(0, 3), [
        400 - 800,   // A->E
        300 - 400,   // E->I
        500 - 300,   // I->O
        350 - 500    // O->U
    ]));
    f1 = f1 * formant_shift;
    
    f2 = Select.kr((vowel * 4).floor.clip(0, 4), [1200, 2200, 2300, 900, 700]);
    f2 = f2 + ((vowel * 4).frac * Select.kr((vowel * 4).floor.clip(0, 3), [
        2200 - 1200,
        2300 - 2200,
        900 - 2300,
        700 - 900
    ]));
    f2 = f2 * formant_shift;
    
    f3 = Select.kr((vowel * 4).floor.clip(0, 4), [2500, 2600, 3000, 2400, 2400]);
    f3 = f3 + ((vowel * 4).frac * Select.kr((vowel * 4).floor.clip(0, 3), [
        2600 - 2500,
        3000 - 2600,
        2400 - 3000,
        2400 - 2400
    ]));
    f3 = f3 * formant_shift;
    
    // Bandwidth (Q) - narrower = more resonant
    bw = 100 * formant_width;
    
    // Three parallel formant filters
    formants = BPF.ar(source, f1.clip(100, 5000), bw / f1.max(100)) * 1.0;
    formants = formants + (BPF.ar(source, f2.clip(100, 8000), bw / f2.max(100)) * 0.7);
    formants = formants + (BPF.ar(source, f3.clip(100, 10000), (bw * 1.5) / f3.max(100)) * 0.5);
    
    sig = formants * 2;  // Boost after filtering

    // === ADDITIONAL FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
