/*
TETHER Generator
The umbilical cable - connection between human and machine

Features:
  - Air/fluid flow through tube
  - Pressure fluctuations
  - Connection pulse rhythm
  - Cable flex and movement
  - Data transfer sounds

Custom params:
  - P1 flow: Flow through tube
  - P2 pressure: Pressure variations
  - P3 pulse: Rhythmic connection pulse
  - P4 flex: Physical cable movement
  - P5 data: Digital data transfer

The cord that binds.
*/

SynthDef(\tether, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                     filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                     midiTrigBus=0, slotIndex=0,
                     customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var flow, pressure, pulse, flex, data;
    var trig;
    var flowSig, pressureSig, pulseSig, flexSig, dataSig;
    var flowNoise, flowMod;
    var pressureOsc, pressureLFO;
    var pulseOsc, pulseEnv;
    var flexNoise, flexMod;
    var dataTrig, dataOsc;
    
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
    flow = In.kr(customBus0);
    flow = Lag.kr(flow, 0.05);
    pressure = In.kr(customBus1);
    pressure = Lag.kr(pressure, 0.05);
    pulse = In.kr(customBus2);
    flex = In.kr(customBus3);
    flex = Lag.kr(flex, 0.05);
    data = In.kr(customBus4);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === FLOW (through tube) ===
    // Filtered noise suggesting air/fluid movement
    flowNoise = PinkNoise.ar;
    flowMod = LFNoise2.kr(1 + (flow * 3)).range(0.7, 1.3);
    flowSig = BPF.ar(flowNoise, 600 * flowMod, 0.4);
    flowSig = flowSig + (BPF.ar(flowNoise, 1200 * flowMod, 0.3) * 0.5);
    // Tube resonance
    flowSig = flowSig + (Resonz.ar(flowNoise, 400, 0.08) * 0.4);
    flowSig = flowSig * flow * 0.4;
    
    // === PRESSURE (fluctuations) ===
    // Low frequency variations suggesting pressure changes
    pressureLFO = LFNoise2.kr(0.5).range(0.9, 1.1);
    pressureOsc = SinOsc.ar(freq * 0.25 * pressureLFO);
    pressureOsc = pressureOsc + (SinOsc.ar(freq * 0.26) * 0.4);  // Beating
    // Pressure "whoosh"
    pressureOsc = pressureOsc + (
        LPF.ar(BrownNoise.ar, 200 + (LFNoise2.kr(0.3).range(0, 200))) * 0.3
    );
    pressureSig = pressureOsc * pressure * 0.4 * LFTri.kr(0.2).range(0.6, 1);
    
    // === PULSE (connection rhythm) ===
    // Regular pulse suggesting data/energy transfer
    pulseEnv = EnvGen.ar(Env.perc(0.01, 0.2), trig + Impulse.ar(0.8 * (1 + pulse)));
    pulseOsc = SinOsc.ar(freq);
    pulseOsc = pulseOsc + (SinOsc.ar(freq * 2) * 0.3);
    // Add "blip" character
    pulseOsc = pulseOsc + (SinOsc.ar(freq * 4) * pulseEnv.squared * 0.2);
    pulseSig = pulseOsc * pulseEnv * pulse * 0.5;
    
    // === FLEX (cable movement) ===
    // Physical cable sounds - creaking, swaying
    flexNoise = PinkNoise.ar;
    flexMod = LFNoise1.kr(0.5 + (flex * 2));
    flexSig = BPF.ar(flexNoise, 300 + (flexMod * 200), 0.2);
    // Occasional stress sounds
    flexSig = flexSig + (
        Resonz.ar(Dust.ar(flex * 5), 500, 0.05) * 4
    );
    // Low swaying
    flexSig = flexSig + (
        SinOsc.ar(freq * 0.125 * (1 + (flexMod * 0.1))) * 
        LFNoise2.kr(0.2).range(0, 0.3)
    );
    flexSig = flexSig * flex * 0.3;
    
    // === DATA (transfer sounds) ===
    // Digital chirps and bursts
    dataTrig = trig + Dust.ar(data * 10);
    dataOsc = SinOsc.ar(freq * 8 * TRand.ar(0.5, 2, dataTrig));
    dataOsc = dataOsc * EnvGen.ar(Env.perc(0.001, 0.03), dataTrig);
    // Bitcrushed texture
    dataOsc = dataOsc + (
        (LFPulse.ar(freq * 16, 0, LFNoise0.kr(20).range(0.1, 0.9)) * 0.2) *
        EnvGen.ar(Env.perc(0.001, 0.05), Dust.ar(data * 5))
    );
    dataSig = HPF.ar(dataOsc, 1000) * data * 0.3;
    
    // === MIX ===
    sig = flowSig + pressureSig + pulseSig + flexSig + dataSig;
    
    // Soft limiting
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.12, 0.18);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ tether loaded".postln;
