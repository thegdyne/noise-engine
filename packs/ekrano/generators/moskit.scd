SynthDef(\forge_ekrano_moskit, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var lock, scan, burn, seek, tone;
    var masterFreq, slaveRatio, syncSig, fmMod, scanMod, seekOsc;

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

    // Custom params
    lock = In.kr(customBus0).linlin(0, 1, 1.0, 4.0);
    scan = In.kr(customBus1).linexp(0, 1, 0.2, 12);
    burn = In.kr(customBus2).linlin(0, 1, 0.5, 8);
    seek = In.kr(customBus3).linlin(0, 1, 0.5, 3);
    tone = In.kr(customBus4);

    // Master frequency
    masterFreq = freq;

    // Scanning modulation
    scanMod = LFTri.kr(scan).range(0.95, 1.05);

    // Hard sync using SyncSaw
    syncSig = SyncSaw.ar(masterFreq, masterFreq * lock * scanMod);

    // FM modulation for burn/afterburner character
    fmMod = SinOsc.ar(masterFreq * seek) * burn * masterFreq;
    seekOsc = SinOsc.ar(masterFreq + fmMod);

    // Mix sync and FM
    sig = (syncSig * 0.5) + (seekOsc * 0.5);

    // Tone control via filtering
    sig = SelectX.ar(tone, [LPF.ar(sig, 2000), sig]);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ekrano_moskit loaded".postln;
