"""
imaginarium/methods/spectral/spectral_drone.py
Spectral drone synthesis - FFT-based frozen/smeared textures

Character: Frozen, ethereal, glacial, evolving
Tags: SPEC, FFT, freeze, ambient
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class SpectralDroneTemplate(MethodTemplate):
    """FFT-based spectral freezing and smearing for drone textures."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="spectral/spectral_drone",
            family="spectral",
            display_name="Spectral Drone",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="freeze",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.7,
                    curve="lin",
                    label="FRZ",
                    tooltip="Spectral freeze amount",
                    unit="",
                ),
                ParamAxis(
                    name="smear",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="SMR",
                    tooltip="Spectral blur/diffusion",
                    unit="",
                ),
                ParamAxis(
                    name="shift",
                    min_val=0.5,
                    max_val=2.0,
                    default=1.0,
                    curve="exp",
                    label="SHF",
                    tooltip="Spectral pitch shift",
                    unit="x",
                ),
                ParamAxis(
                    name="feedback",
                    min_val=0.0,
                    max_val=0.95,
                    default=0.6,
                    curve="lin",
                    label="FBK",
                    tooltip="Spectral feedback amount",
                    unit="",
                ),
                ParamAxis(
                    name="sparkle",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="SPK",
                    tooltip="Random bin excitation",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="stasis",
                    param_weights={
                        "freeze": 1.0,
                        "feedback": 0.7,
                    },
                ),
                MacroControl(
                    name="evolution",
                    param_weights={
                        "smear": 0.8,
                        "sparkle": 1.0,
                    },
                ),
            ],
            default_tags={"topology": "spectral", "character": "frozen", "role": "bed"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "spectral",
            "character": "frozen",
            "role": "bed",
            "family": "spectral",
            "method": self._definition.method_id,
        }
        
        freeze = params.get("freeze", 0.7)
        if freeze > 0.8:
            tags["motion"] = "static"
        elif freeze < 0.3:
            tags["motion"] = "fluid"
        
        sparkle = params.get("sparkle", 0.3)
        if sparkle > 0.6:
            tags["texture"] = "sparkling"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        freeze_read = axes["freeze"].sc_read_expr("customBus0", 0)
        smear_read = axes["smear"].sc_read_expr("customBus1", 1)
        shift_read = axes["shift"].sc_read_expr("customBus2", 2)
        feedback_read = axes["feedback"].sc_read_expr("customBus3", 3)
        sparkle_read = axes["sparkle"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var freeze, smear, shift, feedback, sparkle;
    var source, chain, chainL, chainR;
    var binShift, smearBins;

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
    {freeze_read}
    {smear_read}
    {shift_read}
    {feedback_read}
    {sparkle_read}

    // === SOURCE (rich harmonic content to freeze) ===
    source = Saw.ar(freq) * 0.3;
    source = source + (Pulse.ar(freq * 0.5, 0.3) * 0.2);
    source = source + (PinkNoise.ar * sparkle * 0.2);
    source = source + (SinOsc.ar(freq * 2) * 0.15);
    
    // === SPECTRAL PROCESSING ===
    // FFT analysis
    chainL = FFT(LocalBuf(2048), source + (PinkNoise.ar * 0.01));
    chainR = FFT(LocalBuf(2048), source + (PinkNoise.ar * 0.01));
    
    // Spectral smear (blur in time)
    smearBins = (smear * 32).round;
    chainL = PV_MagSmear(chainL, smearBins);
    chainR = PV_MagSmear(chainR, smearBins);
    
    // Spectral freeze
    chainL = PV_MagFreeze(chainL, freeze > 0.5);
    chainR = PV_MagFreeze(chainR, freeze > 0.5);
    
    // Pitch shift via bin shift
    binShift = ((shift - 1) * 100).round;
    chainL = PV_BinShift(chainL, 1, binShift);
    chainR = PV_BinShift(chainR, 1, binShift + 1);  // Slight stereo offset
    
    // Random bin scramble for sparkle
    chainL = PV_BinScramble(chainL, sparkle * 0.3, sparkle * 0.5, LFNoise0.kr(2));
    chainR = PV_BinScramble(chainR, sparkle * 0.3, sparkle * 0.5, LFNoise0.kr(2.1));
    
    // Back to time domain
    sig = [IFFT(chainL), IFFT(chainR)];
    
    // Add feedback path
    sig = sig + (LocalIn.ar(2) * feedback);
    LocalOut.ar(sig * 0.9);
    
    // Soft limiting
    sig = sig.tanh;

    // === OUTPUT CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
