// Terminal -- maximum velocity, blur of speed
// Role: motion

SynthDef(\forge_icarus_terminal, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var velocity, blur, mach, wake, doppler;
    var tone, chorusL, chorusR, noise, dopplerMod;

    // Standard reads
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
    amp = In.kr(~params[\amplitude]);

    // Theme params
    velocity = In.kr(customBus0).linlin(0, 1, 0.3, 1.0);   // Overall intensity
    blur = In.kr(customBus1).linlin(0, 1, 0.001, 0.02);    // Chorus depth (time)
    mach = In.kr(customBus2).linexp(0, 1, 1000, 12000);    // Edge filter freq
    wake = In.kr(customBus3).linlin(0, 1, 0.0, 0.5);       // Noise wake level
    doppler = In.kr(customBus4).linlin(0, 1, 0.0, 0.1);    // Pitch mod depth

    // Doppler frequency modulation
    dopplerMod = LFNoise2.kr(2, doppler, 1);

    // Core tone - sawtooth for harmonic richness
    tone = Saw.ar(freq * dopplerMod);

    // Motion blur - stereo chorus effect
    chorusL = DelayC.ar(tone, 0.05, SinOsc.kr(0.8, 0, blur, blur + 0.001));
    chorusR = DelayC.ar(tone, 0.05, SinOsc.kr(0.9, pi, blur, blur + 0.001));

    // Mach edge - resonant filter at the sound barrier
    chorusL = RLPF.ar(chorusL, mach, 0.3);
    chorusR = RLPF.ar(chorusR, mach, 0.3);

    // Turbulent wake - filtered noise trail
    noise = PinkNoise.ar(wake);
    noise = BPF.ar(noise, freq, 0.5);

    // Combine with velocity weight
    sig = [chorusL + (noise * 0.5), chorusR + (noise * 0.5)] * velocity;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_icarus_terminal loaded".postln;
