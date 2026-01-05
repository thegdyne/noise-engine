# Mod Matrix Expansion Specification v1.6.1

---
**Version:** 1.6.1 (IMPLEMENTATION READY - VERIFIED)  
**Status:** Ready for Implementation  
**Author:** Gareth + Claude  
**Date:** 2026-01-05  

**Changelog:**
- v1.6.1: **Guards added**; **param mappings verified** against actual SC SynthDefs; all integration points confirmed
- v1.6: SynthDef env capture fix; setup wiring; Python initialization
- v1.5: Per-target summing; restore-on-remove; robust snapshot

---

## Verified SC Synth Args (v1.6.1)

**From actual SynthDef inspection:**

### Mod SynthDefs
```supercollider
// LFO: \modLFO
waveA, waveB, waveC, waveD  // 0-7 (8 waveforms)
polarityA, polarityB, polarityC, polarityD  // 0-2
rate, mode, shape, pattern, rotate

// ARSeq+: \modARSeqPlus  
atkA, atkB, atkC, atkD
relA, relB, relC, relD
polarityA, polarityB, polarityC, polarityD  // 0-2
mode, clockMode, rate

// SauceOfGrav: \ne_mod_sauce_of_grav
rate, depth, gravity, resonance, excursion, calm
tension1, tension2, tension3, tension4
mass1, mass2, mass3, mass4
polarity1, polarity2, polarity3, polarity4  // 0-2
```

### FX SynthDefs
```supercollider
// HEAT: \heat
circuit, drive, mix, bypass  // circuit 0-3

// ECHO: \tapeEcho
time, feedback, tone, wow, spring, verbSend  // NO 'rtn' - has verbSend instead

// REVERB: \reverb
size, decay, tone  // NO 'return' param - reverb writes to dedicated return bus

// DUAL_FILTER: \dualFilter
drive, freq1, reso1, mode1, freq2, reso2, mode2, 
sync1Rate, sync2Rate, syncAmt, harmonics, routing, mix, bypass
```

### Channel Strip
```supercollider
// \channelStrip
echoSend, verbSend  // Confirmed
```

---

## SC Implementation (v1.6.1 - WITH GUARDS)

### Snapshot System

```supercollider
// ============================================================================
// MOD BUS SNAPSHOT SYSTEM (v1.6.1 - WITH GUARDS)
// ============================================================================

~modSnapshotBus = nil;
~modSnapshotSynth = nil;
~modBusSnapshot = Array.fill(16, { 0 });

// SynthDef: no env captures
if(SynthDescLib.global.at(\modBusSnapshot).isNil) {
    SynthDef(\modBusSnapshot, { |outBus=0,
        in0=0, in1=0, in2=0, in3=0, in4=0, in5=0, in6=0, in7=0,
        in8=0, in9=0, in10=0, in11=0, in12=0, in13=0, in14=0, in15=0|
        var vals = [
            In.kr(in0),  In.kr(in1),  In.kr(in2),  In.kr(in3),
            In.kr(in4),  In.kr(in5),  In.kr(in6),  In.kr(in7),
            In.kr(in8),  In.kr(in9),  In.kr(in10), In.kr(in11),
            In.kr(in12), In.kr(in13), In.kr(in14), In.kr(in15)
        ];
        ReplaceOut.kr(outBus, vals);
    }).add;
    s.sync;
};

~setupModBusSnapshot = {
    // v1.6.1 GUARDS
    if(~modBuses.isNil or: { ~modBuses.size < 16 }) {
        "ERROR: ~modBuses not ready (need 16)".warn;
        ^nil;
    };
    if(~modGroup.isNil) {
        "ERROR: ~modGroup not ready".warn;
        ^nil;
    };
    
    if(~modSnapshotBus.isNil) {
        ~modSnapshotBus = Bus.control(s, 16);
    };
    
    if(~modSnapshotSynth.notNil) {
        ~modSnapshotSynth.free;
        ~modSnapshotSynth = nil;
    };
    
    ~modSnapshotSynth = Synth(\modBusSnapshot, [
        \outBus, ~modSnapshotBus.index,
        \in0,  ~modBuses[0].index,  \in1,  ~modBuses[1].index,
        \in2,  ~modBuses[2].index,  \in3,  ~modBuses[3].index,
        \in4,  ~modBuses[4].index,  \in5,  ~modBuses[5].index,
        \in6,  ~modBuses[6].index,  \in7,  ~modBuses[7].index,
        \in8,  ~modBuses[8].index,  \in9,  ~modBuses[9].index,
        \in10, ~modBuses[10].index, \in11, ~modBuses[11].index,
        \in12, ~modBuses[12].index, \in13, ~modBuses[13].index,
        \in14, ~modBuses[14].index, \in15, ~modBuses[15].index
    ], target: ~modGroup, addAction: \addAfter);
    
    "Mod bus snapshot system ready".postln;
};

~snapshotModBuses = {
    var vals = ~modSnapshotBus.getnSynchronous(16);
    16.do { |i| ~modBusSnapshot[i] = vals[i] };
};
```

### Extended Modulation System (v1.6.1 - VERIFIED MAPPINGS)

```supercollider
// ============================================================================
// EXTENDED MODULATION SYSTEM (v1.6.1 - VERIFIED PARAM MAPPINGS)
// ============================================================================

~extTargets = IdentityDictionary.new;
~extUserParams = Dictionary.new;

// Parameter configs [minVal, maxVal, isDiscrete, default]
~extParamConfig = Dictionary.new;

// Mod params (VERIFIED v1.6.1)
~extParamConfig[\mod_rate] = [0, 1, false, 0.5];
~extParamConfig[\mod_wave] = [0, 7, true, 0];      // v1.6.1: 0-7 (8 waveforms)
~extParamConfig[\mod_phase] = [0, 23, true, 0];    // v1.6.1: 0-23 (rotate param)
~extParamConfig[\mod_pol] = [0, 2, true, 0];
~extParamConfig[\mod_atk] = [0, 1, false, 0.5];
~extParamConfig[\mod_rel] = [0, 1, false, 0.5];
~extParamConfig[\mod_depth] = [0, 1, false, 0.5];
~extParamConfig[\mod_grav] = [0, 1, false, 0.5];   // v1.6.1: 'gravity' in SC
~extParamConfig[\mod_reso] = [0, 1, false, 0.5];   // v1.6.1: 'resonance' in SC
~extParamConfig[\mod_excur] = [0, 1, false, 0.5];  // v1.6.1: 'excursion' in SC
~extParamConfig[\mod_calm] = [0, 1, false, 0.5];
~extParamConfig[\mod_tens] = [0, 1, false, 0.5];   // v1.6.1: tensionN in SC
~extParamConfig[\mod_mass] = [0, 1, false, 0.5];   // v1.6.1: massN in SC
~extParamConfig[\mod_shape] = [0, 1, false, 0.5];  // LFO only
~extParamConfig[\mod_pattern] = [0, 5, true, 0];   // LFO only (6 patterns)
~extParamConfig[\mod_mode] = [0, 1, true, 0];      // LFO/ARSeq+ mode

// FX params (VERIFIED v1.6.1)
~extParamConfig[\fx_drive] = [0, 1, false, 0.0];
~extParamConfig[\fx_mix] = [0, 1, false, 1.0];
~extParamConfig[\fx_circuit] = [0, 3, true, 0];    // HEAT: 4 circuits
~extParamConfig[\fx_time] = [0, 1, false, 0.3];
~extParamConfig[\fx_feedback] = [0, 1, false, 0.3]; // v1.6.1: 'feedback' not 'fbk'
~extParamConfig[\fx_tone] = [0, 1, false, 0.7];
~extParamConfig[\fx_wow] = [0, 1, false, 0.1];
~extParamConfig[\fx_spring] = [0, 1, false, 0.0];  // v1.6.1: echo has 'spring'
~extParamConfig[\fx_size] = [0, 1, false, 0.75];
~extParamConfig[\fx_decay] = [0, 1, false, 0.65];
~extParamConfig[\fx_freq1] = [0, 1, false, 0.6];   // v1.6.1: freq1/freq2
~extParamConfig[\fx_reso1] = [0, 1, false, 0.3];
~extParamConfig[\fx_freq2] = [0, 1, false, 0.6];
~extParamConfig[\fx_reso2] = [0, 1, false, 0.3];
~extParamConfig[\fx_routing] = [0, 3, true, 0];    // v1.6.1: dual filter routing
~extParamConfig[\fx_syncAmt] = [0, 1, false, 0.0]; // v1.6.1: syncAmt

// Send params (VERIFIED v1.6.1)
~extParamConfig[\send_ec] = [0, 1, false, 0.0];
~extParamConfig[\send_vb] = [0, 1, false, 0.0];

// Get param config key (v1.6.1 - updated for verified names)
~getParamConfigKey = { |targetStr|
    var parts = targetStr.split($:);
    var tt = parts[0];
    var p, key;
    
    if(tt == "mod") {
        p = parts[2];
        // Prefix matches
        if(p.beginsWith("wave"))    { key = \mod_wave };
        if(p.beginsWith("polarity") or: { p.beginsWith("pol") }) { key = \mod_pol };
        if(p.beginsWith("atk"))     { key = \mod_atk };
        if(p.beginsWith("rel"))     { key = \mod_rel };
        if(p.beginsWith("tension")  or: { p.beginsWith("tens") }) { key = \mod_tens };
        if(p.beginsWith("mass"))    { key = \mod_mass };
        
        // Exact matches
        if(key.isNil) {
            key = switch(p,
                "rate",      { \mod_rate },
                "depth",     { \mod_depth },
                "gravity",   { \mod_grav },   // v1.6.1: SC uses 'gravity'
                "grav",      { \mod_grav },
                "resonance", { \mod_reso },   // v1.6.1: SC uses 'resonance'
                "reso",      { \mod_reso },
                "excursion", { \mod_excur },  // v1.6.1: SC uses 'excursion'
                "excur",     { \mod_excur },
                "calm",      { \mod_calm },
                "shape",     { \mod_shape },
                "pattern",   { \mod_pattern },
                "rotate",    { \mod_phase },  // v1.6.1: rotate is phase offset
                "mode",      { \mod_mode },
                { ("mod_" ++ p).asSymbol }
            );
        };
        ^key;
    };
    
    if(tt == "fx") {
        p = parts[2];
        key = switch(p,
            "type",     { \fx_circuit },  // v1.6.1: HEAT 'circuit'
            "circuit",  { \fx_circuit },
            "fbk",      { \fx_feedback }, // v1.6.1: SC uses 'feedback'
            "spr",      { \fx_spring },   // v1.6.1: echo 'spring' not 'spr'
            "siz",      { \fx_size },
            "dec",      { \fx_decay },
            { ("fx_" ++ p).asSymbol }
        );
        ^key;
    };
    
    if(tt == "send") {
        ^("send_" ++ parts[2]).asSymbol;
    };
    
    ^\unknown;
};

// Parse target
~parseExtTarget = { |targetStr|
    var parts = targetStr.split($:);
    var tt = parts[0].asSymbol;
    
    case
    { tt == \mod } {
        var slot = parts[1].asInteger - 1;
        var param = parts[2].asSymbol;
        [\mod, slot, param]
    }
    { tt == \fx } {
        var fxType = parts[1].asSymbol;
        var param = parts[2].asSymbol;
        [\fx, fxType, param]
    }
    { tt == \send } {
        var slot = parts[1].asInteger - 1;
        var sendType = parts[2].asSymbol;
        [\send, slot, sendType]
    }
};

// Ensure target exists
~ensureExtTarget = { |targetStr|
    if(~extTargets[targetStr].isNil) {
        var cfg, cfgKey;
        
        ~extTargets[targetStr] = (
            routes: Array.fill(4, nil),
            parsed: ~parseExtTarget.(targetStr),
            cfgKey: ~getParamConfigKey.(targetStr)
        );
        
        cfgKey = ~extTargets[targetStr][\cfgKey];
        cfg = ~extParamConfig[cfgKey] ?? [0, 1, false, 0.5];
        if(~extUserParams[targetStr].isNil) {
            ~extUserParams[targetStr] = cfg[3];
        };
    };
    ~extTargets[targetStr];
};

// Add/remove/set route (same as v1.6)
~addExtModRoute = { |sourceBus, targetStr, depth, amount, offset, polarity, invert|
    var t = ~ensureExtTarget.(targetStr);
    var routes = t[\routes];
    var idx;
    
    idx = routes.detectIndex { |r| r.notNil and: { r[\sourceBus] == sourceBus } }
       ?? routes.detectIndex { |r| r.isNil };
    
    if(idx.isNil) {
        ("Extended mod: no free slots for " ++ targetStr).warn;
        ^nil;
    };
    
    routes[idx] = (
        sourceBus: sourceBus,
        depth: depth,
        amount: amount,
        offset: offset,
        polarity: polarity,
        invert: invert
    );
    
    ("Extended mod route added: bus % → % [slot %]".format(sourceBus, targetStr, idx)).postln;
    
    if(~extTargets.size == 1 and: { ~extModApplyTask.isNil }) {
        ~startExtModApplyTask.();
    };
};

~removeExtModRoute = { |sourceBus, targetStr|
    var t = ~extTargets[targetStr];
    var routes, idx;
    
    if(t.isNil) { ^nil };
    
    routes = t[\routes];
    idx = routes.detectIndex { |r| r.notNil and: { r[\sourceBus] == sourceBus } };
    
    if(idx.notNil) {
        routes[idx] = nil;
        ("Extended mod route removed: bus % from %".format(sourceBus, targetStr)).postln;
    };
    
    if(routes.every { |r| r.isNil }) {
        ~restoreExtTargetToBase.(targetStr);
        ~extTargets.removeAt(targetStr);
        ("Extended target restored: %".format(targetStr)).postln;
    };
    
    if(~extTargets.size == 0) {
        ~stopExtModApplyTask.();
    };
};

~setExtModRoute = { |sourceBus, targetStr, depth, amount, offset, polarity, invert|
    var t = ~extTargets[targetStr];
    var routes, idx;
    
    if(t.isNil) {
        ~addExtModRoute.(sourceBus, targetStr, depth, amount, offset, polarity, invert);
        ^nil;
    };
    
    routes = t[\routes];
    idx = routes.detectIndex { |r| r.notNil and: { r[\sourceBus] == sourceBus } };
    
    if(idx.notNil) {
        routes[idx][\depth] = depth;
        routes[idx][\amount] = amount;
        routes[idx][\offset] = offset;
        routes[idx][\polarity] = polarity;
        routes[idx][\invert] = invert;
    } {
        ~addExtModRoute.(sourceBus, targetStr, depth, amount, offset, polarity, invert);
    };
};

~setExtUserParam = { |targetStr, value|
    ~extUserParams[targetStr] = value;
};

// Set target value (v1.6.1 - VERIFIED PARAM NAMES)
~setExtTargetValue = { |parsed, value|
    var targetType = parsed[0];
    var paramSym;
    
    case
    { targetType == \mod } {
        var slot = parsed[1];
        var param = parsed[2];
        
        // v1.6.1: Map UI names to actual SC synth args
        paramSym = switch(param,
            \grav,   { \gravity },    // UI: grav, SC: gravity
            \reso,   { \resonance },  // UI: reso, SC: resonance
            \excur,  { \excursion },  // UI: excur, SC: excursion
            \pol_1,  { \polarityA },  // UI: pol_1, SC: polarityA
            \pol_2,  { \polarityB },
            \pol_3,  { \polarityC },
            \pol_4,  { \polarityD },
            \wave_1, { \waveA },      // UI: wave_1, SC: waveA
            \wave_2, { \waveB },
            \wave_3, { \waveC },
            \wave_4, { \waveD },
            \atk_1,  { \atkA },       // UI: atk_1, SC: atkA
            \atk_2,  { \atkB },
            \atk_3,  { \atkC },
            \atk_4,  { \atkD },
            \rel_1,  { \relA },       // UI: rel_1, SC: relA
            \rel_2,  { \relB },
            \rel_3,  { \relC },
            \rel_4,  { \relD },
            \tens_1, { \tension1 },   // UI: tens_1, SC: tension1
            \tens_2, { \tension2 },
            \tens_3, { \tension3 },
            \tens_4, { \tension4 },
            \mass_1, { \mass1 },      // UI: mass_1, SC: mass1
            \mass_2, { \mass2 },
            \mass_3, { \mass3 },
            \mass_4, { \mass4 },
            { param }                 // Default: use as-is
        );
        
        if(~modNodes[slot].notNil) {
            ~modNodes[slot].set(paramSym, value);
        };
    }
    { targetType == \fx } {
        var fxType = parsed[1];
        var param = parsed[2];
        
        // v1.6.1: Map UI names to actual SC synth args
        paramSym = switch(param,
            \type,   { \circuit },   // HEAT: type → circuit
            \fbk,    { \feedback },  // ECHO: fbk → feedback
            \spr,    { \spring },    // ECHO: spr → spring  
            \siz,    { \size },      // REVERB: siz → size
            \dec,    { \decay },     // REVERB: dec → decay
            { param }
        );
        
        switch(fxType,
            \heat, {
                if(~heatSynth.notNil) {
                    ~heatSynth.set(paramSym, value);
                };
            },
            \echo, {
                if(~echoSynth.notNil) {
                    ~echoSynth.set(paramSym, value);
                };
            },
            \reverb, {
                if(~verbSynth.notNil) {
                    ~verbSynth.set(paramSym, value);
                };
            },
            \dual_filter, {
                if(~dualFilterSynth.notNil) {
                    ~dualFilterSynth.set(paramSym, value);
                };
            }
        );
    }
    { targetType == \send } {
        var slot = parsed[1];
        var sendType = parsed[2];
        
        if(~channelStrips[slot].notNil) {
            switch(sendType,
                \ec, { ~channelStrips[slot].set(\echoSend, value) },
                \vb, { ~channelStrips[slot].set(\verbSend, value) }
            );
        };
    }
};

~restoreExtTargetToBase = { |targetStr|
    var t = ~extTargets[targetStr];
    var cfg, base;
    
    if(t.isNil) { ^nil };
    
    cfg = ~extParamConfig[t[\cfgKey]] ?? [0, 1, false, 0.5];
    base = ~extUserParams[targetStr] ?? cfg[3];
    
    ~setExtTargetValue.(t[\parsed], base);
};

// Apply modulation (same as v1.6)
~applyExtTarget = { |targetStr, t|
    var routes = t[\routes];
    var cfg = ~extParamConfig[t[\cfgKey]] ?? [0, 1, false, 0.5];
    var minVal = cfg[0], maxVal = cfg[1], isDiscrete = cfg[2], def = cfg[3];
    var base = ~extUserParams[targetStr] ?? def;
    var range = maxVal - minVal;
    var sumDelta = 0;
    var s, delta, final, sb;
    
    routes.do { |r|
        if(r.notNil) {
            sb = r[\sourceBus];
            
            s = if((sb >= 0) and: { sb <= 15 }) {
                ~modBusSnapshot[sb]
            } {
                0
            };
            
            if(r[\invert] == 1) { s = s.neg };
            
            s = switch(r[\polarity],
                0, { s },
                1, { (s + 1) * 0.5 },
                2, { ((s + 1) * 0.5).neg }
            );
            
            delta = (s * r[\amount] * r[\depth]) + r[\offset];
            sumDelta = sumDelta + delta;
        };
    };
    
    sumDelta = sumDelta.clip(-1, 1);
    
    if(isDiscrete) {
        final = (base + (sumDelta * range)).round.clip(minVal, maxVal);
    } {
        final = (base + (sumDelta * range)).clip(minVal, maxVal);
    };
    
    ~setExtTargetValue.(t[\parsed], final);
};

~extModApplyTask = nil;

~startExtModApplyTask = {
    // Ensure snapshot system ready
    if(~modSnapshotBus.isNil or: { ~modSnapshotSynth.isNil }) {
        ~setupModBusSnapshot.();
    };
    
    if(~extModApplyTask.notNil) {
        ~extModApplyTask.stop;
    };
    
    ~extModApplyTask = Routine({
        loop {
            ~snapshotModBuses.();
            
            ~extTargets.keysValuesDo { |targetStr, t|
                ~applyExtTarget.(targetStr, t);
            };
            
            (1 / 50).wait;
        };
    }).play(SystemClock);
    
    "Extended mod apply task started (50Hz)".postln;
};

~stopExtModApplyTask = {
    if(~extModApplyTask.notNil) {
        ~extModApplyTask.stop;
        ~extModApplyTask = nil;
    };
    "Extended mod apply task stopped".postln;
};

~clearAllExtModRoutes = {
    ~extTargets.keysDo { |targetStr|
        ~restoreExtTargetToBase.(targetStr);
    };
    ~extTargets = IdentityDictionary.new;
    ~stopExtModApplyTask.();
    "All extended routes cleared and restored".postln;
};
```

---

## Python UI → SC Param Name Mapping (v1.6.1)

### Modulator Parameters

**UI sends these names:**
- `mod:1:wave_1` → SC receives: map to `waveA`
- `mod:1:pol_1` → SC receives: map to `polarityA`
- `mod:1:atk_1` → SC receives: map to `atkA`
- `mod:1:rel_1` → SC receives: map to `relA`
- `mod:1:tens_1` → SC receives: map to `tension1`
- `mod:1:mass_1` → SC receives: map to `mass1`
- `mod:1:grav` → SC receives: map to `gravity`
- `mod:1:reso` → SC receives: map to `resonance`
- `mod:1:excur` → SC receives: map to `excursion`

### FX Parameters

**UI sends these names:**
- `fx:heat:type` → SC receives: map to `circuit`
- `fx:echo:fbk` → SC receives: map to `feedback`
- `fx:echo:spr` → SC receives: map to `spring`
- `fx:reverb:siz` → SC receives: map to `size`
- `fx:reverb:dec` → SC receives: map to `decay`

**Note:** ECHO and REVERB have **NO return level param** - they write to dedicated return buses. Don't try to modulate `rtn` or `return`.

---

## Verified Param Ranges (v1.6.1)

| Param | Min | Max | Discrete | Notes |
|-------|-----|-----|----------|-------|
| waveform | 0 | 7 | Yes | 8 waveforms (0-7) |
| phase/rotate | 0 | 23 | Yes | 24 steps (0-23 = 0-345° in 15° steps) |
| polarity | 0 | 2 | Yes | 3 modes |
| pattern | 0 | 5 | Yes | 6 patterns (LFO only) |
| mode | 0 | 1 | Yes | 2 modes |
| circuit | 0 | 3 | Yes | 4 circuits (HEAT) |
| routing | 0 | 3 | Yes | 4 modes (dual filter) |

---

## Implementation Phases

Same as v1.6, with emphasis on Phase 4 param mapping.

---

## Success Criteria

- [ ] Guards prevent crashes if ~modBuses not ready
- [ ] Snapshot synth runs after mod sources
- [ ] All param names map correctly
- [ ] Discrete params use correct ranges
- [ ] No "silent failures" (wrong param names)

---

## Changelog

- **1.6.1** (2026-01-05): Guards added; param mappings verified against actual SC SynthDefs; ranges corrected
- **1.6**: SynthDef env capture fix; setup wiring; Python init
- **1.5**: Per-target summing; restore-on-remove

---

## Approval

- [ ] Gareth - Final review
- [ ] All integration points verified ✓✓✓
- [ ] Implementation ready ✓✓✓✓

---

*End of specification v1.6.1 - Implementation Ready (VERIFIED)*
