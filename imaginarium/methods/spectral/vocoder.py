"""
imaginarium/methods/spectral/vocoder.py
Vocoder-style synthesis - spectral band transfer

Character: Robotic, processed, sci-fi, talking
Tags: SPEC, vocoder, bands, robotic
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class VocoderTemplate(MethodTemplate):
    """Vocoder-style synthesis using band filtering."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="spectral/vocoder",
            family="spectral",
            display_name="Vocoder",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="bands",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="BND",
                    tooltip="Number of active bands",
                    unit="",
                ),
                ParamAxis(
                    name="resonance",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.6,
                    curve="lin",
                    label="REZ",
                    tooltip="Band filter resonance",
                    unit="",
                ),
                ParamAxis(
                    name="shift",
                    min_val=0.5,
                    max_val=2.0,
                    default=1.0,
                    curve="exp",
                    label="SHF",
                    tooltip="Spectral shift",
                    unit="x",
                ),
                ParamAxis(
                    name="noise_mix",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.3,
                    curve="lin",
                    label="NSE",
                    tooltip="Noise carrier amount",
                    unit="",
                ),
                ParamAxis(
                    name="attack",
                    min_val=0.001,
                    max_val=0.1,
                    default=0.01,
                    curve="exp",
                    label="ATK",
                    tooltip="Band envelope attack",
                    unit="s",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="character",
                    param_weights={
                        "resonance": 1.0,
                        "bands": 0.5,
                    },
                ),
                MacroControl(
                    name="texture",
                    param_weights={
                        "noise_mix": 1.0,
                        "attack": 0.7,
                    },
                ),
            ],
            default_tags={"topology": "vocoder", "character": "robotic"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "vocoder",
            "character": "robotic",
            "family": "spectral",
            "method": self._definition.method_id,
        }
        
        noise_mix = params.get("noise_mix", 0.3)
        if noise_mix > 0.6:
            tags["texture"] = "whispered"
        else:
            tags["texture"] = "tonal"
        
        resonance = params.get("resonance", 0.6)
        if resonance > 0.7:
            tags["quality"] = "resonant"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        
        bands_read = axes["bands"].sc_read_expr("customBus0", 0)
        resonance_read = axes["resonance"].sc_read_expr("customBus1", 1)
        shift_read = axes["shift"].sc_read_expr("customBus2", 2)
        noise_mix_read = axes["noise_mix"].sc_read_expr("customBus3", 3)
        attack_read = axes["attack"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bands, resonance, shift, noise_mix, bandAttack;
    var carrier, modulator, numBands, bandFreqs, bandQ;
    var band1, band2, band3, band4, band5, band6, band7, band8;
    var env1, env2, env3, env4, env5, env6, env7, env8;

    // Seed for determinism
    RandSeed.ir(1, seed);

    // Read standard params
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
    {bands_read}
    {resonance_read}
    {shift_read}
    {noise_mix_read}
    {attack_read}

    // === CARRIER (osc + noise mix) ===
    carrier = Saw.ar(freq) * (1 - noise_mix);
    carrier = carrier + (PinkNoise.ar * noise_mix);
    
    // === MODULATOR (internal oscillator for envelope follower sim) ===
    modulator = LFSaw.ar(freq * 0.5) + (SinOsc.ar(freq) * 0.5);
    modulator = modulator + (LFNoise2.ar(10) * 0.2);
    
    // === BAND FREQUENCIES (8 bands, logarithmically spaced) ===
    bandFreqs = [100, 200, 400, 800, 1600, 3200, 6400, 10000] * shift;
    bandQ = resonance.linlin(0, 1, 0.5, 0.1);
    numBands = bands.linlin(0, 1, 2, 8).round;
    
    // === BAND FILTERS + ENVELOPE FOLLOWERS ===
    // Band 1
    band1 = BPF.ar(carrier, bandFreqs[0].clip(50, 15000), bandQ);
    env1 = Amplitude.kr(BPF.ar(modulator, bandFreqs[0].clip(50, 15000), 0.5), bandAttack, 0.1);
    band1 = band1 * env1 * (numBands >= 1);
    
    // Band 2
    band2 = BPF.ar(carrier, bandFreqs[1].clip(50, 15000), bandQ);
    env2 = Amplitude.kr(BPF.ar(modulator, bandFreqs[1].clip(50, 15000), 0.5), bandAttack, 0.1);
    band2 = band2 * env2 * (numBands >= 2);
    
    // Band 3
    band3 = BPF.ar(carrier, bandFreqs[2].clip(50, 15000), bandQ);
    env3 = Amplitude.kr(BPF.ar(modulator, bandFreqs[2].clip(50, 15000), 0.5), bandAttack, 0.1);
    band3 = band3 * env3 * (numBands >= 3);
    
    // Band 4
    band4 = BPF.ar(carrier, bandFreqs[3].clip(50, 15000), bandQ);
    env4 = Amplitude.kr(BPF.ar(modulator, bandFreqs[3].clip(50, 15000), 0.5), bandAttack, 0.1);
    band4 = band4 * env4 * (numBands >= 4);
    
    // Band 5
    band5 = BPF.ar(carrier, bandFreqs[4].clip(50, 15000), bandQ);
    env5 = Amplitude.kr(BPF.ar(modulator, bandFreqs[4].clip(50, 15000), 0.5), bandAttack, 0.1);
    band5 = band5 * env5 * (numBands >= 5);
    
    // Band 6
    band6 = BPF.ar(carrier, bandFreqs[5].clip(50, 15000), bandQ);
    env6 = Amplitude.kr(BPF.ar(modulator, bandFreqs[5].clip(50, 15000), 0.5), bandAttack, 0.1);
    band6 = band6 * env6 * (numBands >= 6);
    
    // Band 7
    band7 = BPF.ar(carrier, bandFreqs[6].clip(50, 15000), bandQ);
    env7 = Amplitude.kr(BPF.ar(modulator, bandFreqs[6].clip(50, 15000), 0.5), bandAttack, 0.1);
    band7 = band7 * env7 * (numBands >= 7);
    
    // Band 8
    band8 = BPF.ar(carrier, bandFreqs[7].clip(50, 15000), bandQ);
    env8 = Amplitude.kr(BPF.ar(modulator, bandFreqs[7].clip(50, 15000), 0.5), bandAttack, 0.1);
    band8 = band8 * env8 * (numBands >= 8);
    
    // Sum bands
    sig = (band1 + band2 + band3 + band4 + band5 + band6 + band7 + band8) * 2;
    
    // Soft limit
    sig = sig.tanh;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
