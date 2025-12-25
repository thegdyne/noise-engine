// REDFLASH - Bold accent like the bus's red paint
// Family: fm (ring_mod)
// Role: accent

SynthDef(\forge_barbican_hound_redflash, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var gloss, bold, flash, fade, hue;
    var carrier, modulator, ring, env, trig;

    // Standard bus reads
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
    gloss = In.kr(customBus0);  // Brightness
    bold = In.kr(customBus1);   // Intensity
    flash = In.kr(customBus2);  // Attack
    fade = In.kr(customBus3);   // Decay
    hue = In.kr(customBus4);    // Ring mod ratio

    // Trigger selection
    trig = Select.ar(envSource.round.clip(0, 2), [
        Impulse.ar(2),  // OFF: regular pulse
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Flash envelope
    env = EnvGen.ar(
        Env.perc(
            flash.linexp(0, 1, 0.1, 0.001),
            fade.linexp(0, 1, 0.1, 1.5)
        ),
        trig
    );

    // Carrier - rich saw
    carrier = Saw.ar(freq) + (Pulse.ar(freq * 1.01, 0.3) * 0.5);

    // Modulator - ratio based on hue
    modulator = SinOsc.ar(freq * hue.linexp(0, 1, 0.5, 4));

    // Ring modulation
    ring = carrier * modulator;

    // Mix ring with carrier based on bold
    sig = (ring * bold) + (carrier * (1 - bold) * 0.5);

    // Apply envelope
    sig = sig * env;

    // Gloss brightness
    sig = RHPF.ar(sig, gloss.linexp(0, 1, 200, 2000), 0.5);
    sig = LPF.ar(sig, gloss.linexp(0, 1, 3000, 12000));

    // Bold saturation
    sig = (sig * bold.linexp(0, 1, 1, 3)).tanh;

    // Stereo with punch
    sig = Pan2.ar(sig, 0);

    // Post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_barbican_hound_redflash loaded".postln;
