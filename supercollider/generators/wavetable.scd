/*
Wavetable Generator
Interpolating wavetable synthesis with multiple waveforms

Signal flow: Wavetables → Mix/Morph → Filter → ENV VCA → Output

Custom params:
  - P1 wave_position: 0-1 (position in wavetable)
  - P2 wave_morph: 0-1 (crossfade between adjacent waves)
  - P3 detune: 0-1 (oscillator detuning)
  - P4 fold_amount: 0-1 (wavefolding)
  - P5 sub_level: 0-1 (sub oscillator)
*/

SynthDef(\wavetable, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var wavePos, morph, detune, fold, subLevel;
    var osc1, osc2, sub, wave1, wave2, wave3, wave4;
    
    // Standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    wavePos = In.kr(customBus0);
    morph = In.kr(customBus1);
    detune = In.kr(customBus2);
    fold = In.kr(customBus3);
    subLevel = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    wave1 = SinOsc.ar(freq);
    wave2 = LFTri.ar(freq);
    wave3 = Saw.ar(freq);
    wave4 = Pulse.ar(freq, 0.5);
    
    osc1 = SelectX.ar(wavePos * 3, [wave1, wave2, wave3, wave4]);
    osc2 = SelectX.ar(wavePos * 3, [
        SinOsc.ar(freq * (1 + (detune * 0.02))),
        LFTri.ar(freq * (1 - (detune * 0.015))),
        Saw.ar(freq * (1 + (detune * 0.01))),
        Pulse.ar(freq * (1 - (detune * 0.02)), 0.45)
    ]);
    
    sig = (osc1 * (1 - morph)) + (osc2 * morph);
    sig = (sig * (1 + (fold * 4))).fold(-1, 1);
    
    sub = SinOsc.ar(freq * 0.5) * subLevel * 0.5;
    sig = sig + sub;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = sig ! 2;  // Dual mono for channel strip panning
    Out.ar(out, sig);
}).add;

"  ✓ wavetable loaded".postln;
