/*
Subtractive Generator
Classic oscillator + filter synthesis

Signal flow: Oscillators → Mix → Filter → ENV VCA → Output

Custom params:
  - P1 osc_waveform: 0-3 (saw/square/tri/noise)
  - P2 sub_osc_level: 0-1 (sub oscillator amount)
  - P3 osc_mix: 0-1 (OSC1 <-> OSC2 crossfade)
  - P4 noise_amount: 0-1 (noise layer)
  - P5 filter_drive: 0-1 (pre-filter saturation)
*/

SynthDef(\subtractive, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                          midiTrigBus=0, slotIndex=0,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var waveform, subLevel, oscMix, noiseAmt, drive;
    var osc1, osc2, sub, noise, saw, square, tri, noiseOsc;
    
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
    waveform = In.kr(customBus0);
    subLevel = In.kr(customBus1);
    oscMix = In.kr(customBus2);
    noiseAmt = In.kr(customBus3);
    drive = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    saw = Saw.ar(freq);
    square = Pulse.ar(freq, 0.5);
    tri = LFTri.ar(freq);
    noiseOsc = WhiteNoise.ar;
    
    osc1 = SelectX.ar(waveform, [saw, square, tri, noiseOsc]);
    osc2 = SelectX.ar(waveform, [
        Saw.ar(freq * 1.005),
        Pulse.ar(freq * 0.995, 0.45),
        LFTri.ar(freq * 1.003),
        PinkNoise.ar
    ]);
    
    sub = Pulse.ar(freq * 0.5, 0.5) * subLevel;
    noise = WhiteNoise.ar * noiseAmt * 0.5;
    
    sig = ((osc1 * (1 - oscMix)) + (osc2 * oscMix)) * 0.5;
    sig = sig + sub + noise;
    sig = (sig * (1 + (drive * 4))).tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.3, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = sig ! 2;  // Dual mono for channel strip panning
    Out.ar(out, sig);
}).add;

"  ✓ subtractive loaded".postln;
