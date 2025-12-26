/*
forge_template.scd - Reference SynthDef template for Noise Engine packs

NAMING CONVENTION (from imaginarium/naming.py):
  pack_id:       [a-z][a-z0-9_]{2,23}  (3-24 chars, lowercase slug)
  generator_id:  [a-z][a-z0-9_]{0,31}  (1-32 chars, lowercase slug)
  synthdef:      ne_{pack_id}__{generator_id}  (double underscore separator)

EXAMPLE:
  pack_id = "leviathan"
  generator_id = "abyss_drone"
  synthdef = "ne_leviathan__abyss_drone"

Updated: 2025-12-25 - Added portamentoBus
*/

SynthDef(\ne_PACKID__GENERATORID, { |out,
    freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus,
    seed=12345|

    // === VAR DECLARATIONS (must be at block start) ===
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var p1, p2, p3, p4, p5;  // Custom params (themed names in your actual code)

    // === DETERMINISM (must be first executable line) ===
    RandSeed.ir(0, seed);

    // === READ STANDARD BUSES ===
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));  // 1ms to 500ms glide

    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // === READ CUSTOM PARAMS (P1-P5) ===
    // Map normalized 0-1 to actual ranges
    /// IMAG_CUSTOMBUS:0
    p1 = In.kr(customBus0).linlin(0, 1, 0.1, 0.9);  // Example: pulse width
    /// IMAG_CUSTOMBUS:1
    p2 = In.kr(customBus1).linexp(0, 1, 0.5, 8.0);  // Example: detune ratio
    /// IMAG_CUSTOMBUS:2
    p3 = In.kr(customBus2);  // Example: direct 0-1 mix
    /// IMAG_CUSTOMBUS:3
    p4 = In.kr(customBus3);
    /// IMAG_CUSTOMBUS:4
    p5 = In.kr(customBus4);

    // === SOUND SOURCE ===
    // Your synthesis code here
    sig = Saw.ar(freq) * 0.3;

    // === OPTIONAL: Stereo spread for mono sources ===
    sig = ~stereoSpread.(sig, 0.2, 0.3);

    // === MANDATORY POST-CHAIN (this exact order) ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * ne_PACKID__GENERATORID loaded".postln;


/*
============================================================================
QUICK REFERENCE
============================================================================

REQUIRED BUS ARGUMENTS (in order):
  out, freqBus, cutoffBus, resBus, attackBus, decayBus,
  filterTypeBus, envEnabledBus, envSourceBus,
  clockRateBus, clockTrigBus,
  midiTrigBus, slotIndex,
  customBus0, customBus1, customBus2, customBus3, customBus4,
  portamentoBus

HELPER FUNCTIONS (defined in core/helpers.scd):
  ~ensure2ch.(sig)                    - Force stereo output
  ~multiFilter.(sig, type, freq, rq)  - LP/HP/BP/Notch/LP2/OFF filter
  ~envVCA.(sig, src, rate, atk, dec, amp, clockTrig, midiTrig, slot)
  ~stereoSpread.(sig, rate, width)    - Optional mono→stereo with LFO pan

POST-CHAIN ORDER (mandatory):
  1. ~multiFilter
  2. ~envVCA
  3. ~ensure2ch
  4. Out.ar

IMAG_CUSTOMBUS MARKERS:
  Required for Imaginarium method validation.
  Format: /// IMAG_CUSTOMBUS:N  (where N = 0-4)
  Place immediately before each In.kr(customBusN) line.

PORTAMENTO:
  Read portamentoBus and apply Lag.kr to freq:
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
  
  Mapping: 0 = 1ms (instant), 0.5 ≈ 70ms, 1.0 = 500ms

============================================================================
*/
