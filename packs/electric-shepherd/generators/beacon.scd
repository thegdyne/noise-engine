/*
BEACON Generator
Station indicators - lights and status sounds

Features:
  - Status beeps
  - Machine heartbeat
  - Warning signals
  - Ready/standby tone
  - Indicator glow

Custom params:
  - P1 status: Status beep patterns
  - P2 heartbeat: Rhythmic machine pulse
  - P3 warning: Alert sounds
  - P4 ready: Standby tone
  - P5 glow: Continuous indicator presence

The machine's quiet conversation with itself.
*/

SynthDef(\beacon, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                     filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                     midiTrigBus=0, slotIndex=0,
                     customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var status, heartbeat, warning, ready, glow;
    var trig;
    var statusSig, heartbeatSig, warningSig, readySig, glowSig;
    var statusTrig, statusOsc;
    var hbTrig, hbOsc;
    var warnTrig, warnOsc;
    var readyOsc, readyMod;
    var glowOsc, glowLFO;
    
    // Standard params
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
    
    // Custom params with smoothing
    status = In.kr(customBus0);
    heartbeat = In.kr(customBus1);
    warning = In.kr(customBus2);
    ready = In.kr(customBus3);
    ready = Lag.kr(ready, 0.05);
    glow = In.kr(customBus4);
    glow = Lag.kr(glow, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === STATUS (beeps) ===
    // Regular status beeps
    statusTrig = Impulse.ar(1 + (status * 2)) * (LFPulse.kr(0.25, 0, 0.5));  // Beep patterns
    statusOsc = SinOsc.ar(freq * 4);
    statusOsc = statusOsc * EnvGen.ar(Env.perc(0.005, 0.08), statusTrig);
    // Double beep variation
    statusOsc = statusOsc + (
        SinOsc.ar(freq * 5) *
        EnvGen.ar(Env.perc(0.005, 0.06), TDelay.ar(statusTrig, 0.12)) * 0.7
    );
    statusSig = statusOsc * status * 0.4;
    
    // === HEARTBEAT (machine pulse) ===
    // Slow rhythmic pulse like a cardiac monitor
    hbTrig = Impulse.ar(0.8 + (heartbeat * 0.4));
    hbOsc = SinOsc.ar(freq * 2);
    hbOsc = hbOsc * EnvGen.ar(Env.perc(0.01, 0.15), hbTrig);
    // Secondary pulse (like lub-dub)
    hbOsc = hbOsc + (
        SinOsc.ar(freq * 1.5) *
        EnvGen.ar(Env.perc(0.01, 0.1), TDelay.ar(hbTrig, 0.15)) * 0.6
    );
    heartbeatSig = hbOsc * heartbeat * 0.5;
    
    // === WARNING (alerts) ===
    // Urgent repeating tone
    warnTrig = trig + (Impulse.ar(4) * (LFPulse.kr(0.5, 0, 0.3)));  // Intermittent
    warnOsc = SinOsc.ar(freq * 6);
    warnOsc = warnOsc + (SinOsc.ar(freq * 6.5) * 0.5);  // Beating for urgency
    warnOsc = warnOsc * EnvGen.ar(Env.perc(0.001, 0.1), warnTrig);
    // Add harsh component
    warnOsc = warnOsc + (
        Pulse.ar(freq * 3, 0.5) * 
        EnvGen.ar(Env.perc(0.001, 0.05), warnTrig) * 0.3
    );
    warningSig = warnOsc * warning * 0.4;
    
    // === READY (standby tone) ===
    // Gentle continuous tone indicating readiness
    readyMod = SinOsc.kr(0.5).range(0.95, 1.05);
    readyOsc = SinOsc.ar(freq * readyMod) * 0.5;
    readyOsc = readyOsc + (SinOsc.ar(freq * 2 * readyMod) * 0.2);
    // Soft pulsing
    readyOsc = readyOsc * LFTri.kr(0.3).range(0.7, 1);
    readySig = readyOsc * ready * 0.3;
    
    // === GLOW (indicator presence) ===
    // Warm continuous drone suggesting LED glow
    glowLFO = LFNoise2.kr(0.2).range(0.9, 1.1);
    glowOsc = SinOsc.ar(freq * 0.5 * glowLFO) * 0.4;
    glowOsc = glowOsc + (SinOsc.ar(freq * glowLFO) * 0.3);
    // Add subtle warmth
    glowOsc = glowOsc + (LPF.ar(Saw.ar(freq * 0.25), 200) * 0.2);
    glowSig = glowOsc * glow * 0.3 * LFTri.kr(0.1).range(0.8, 1);
    
    // === MIX ===
    sig = statusSig + heartbeatSig + warningSig + readySig + glowSig;
    
    // Soft limiting
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.08, 0.12);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ beacon loaded".postln;
