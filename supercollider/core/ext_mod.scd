// ============================================================================
// EXTENDED MODULATION SYSTEM (v1.7 - P1-P4 CROSS-MODULATION)
// ============================================================================
//
// Purpose: Route modulation to FX/modulator/send parameters (not just generators)
// Features: Per-target summing, discrete param handling, base value restoration
// Usage: ~addExtModRoute.(bus, "fx:heat:drive", depth, amt, off, pol, inv)
//        ~addExtModRoute.(bus, "mod:2:p2", depth, amt, off, pol, inv)  // NEW
//
// P1-P4 targets use ~setModParam which does type-aware mapping:
//   mod:N:p1 -> rate (all types)
//   mod:N:p2 -> globalWave (LFO) / globalAtk (ARSeq+) / globalTension (Sauce)
//   mod:N:p3 -> pattern (LFO) / globalRel (ARSeq+) / calm (Sauce)
//   mod:N:p4 -> globalPolarity (all types)
//
// Part of: Mod Matrix Expansion (MOD_MATRIX_EXPANSION_SPEC_v1.6.1)
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

// P1-P4 standardized params (v1.7 - cross-modulation)
// Range is 0-1, actual mapping handled by ~setModParam in mod_slots.scd
~extParamConfig[\mod_p1] = [0, 1, false, 0.5];     // rate (all types)
~extParamConfig[\mod_p2] = [0, 1, false, 0.5];     // globalWave/globalAtk/globalTension
~extParamConfig[\mod_p3] = [0, 1, false, 0.5];     // pattern/globalRel/calm
~extParamConfig[\mod_p4] = [0, 1, false, 0.5];     // globalPolarity (all types)

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

// Channel strip pan (v1.7)
~extParamConfig[\chan_pan] = [-1, 1, false, 0.0];

// Get param config key (v1.7 - added P1-P4)
~getParamConfigKey = { |targetStr|
    var parts = targetStr.split($:);
    var tt = parts[0];
    var p, key;
    
    if(tt == "mod") {
        p = parts[2];
        
        // P1-P4 standardized params (v1.7)
        if(p == "p1") { ^(\mod_p1) };
        if(p == "p2") { ^(\mod_p2) };
        if(p == "p3") { ^(\mod_p3) };
        if(p == "p4") { ^(\mod_p4) };
        
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
    
    if(tt == "chan") {
        p = parts[2];
        if(p == "pan") { ^(\chan_pan) };
        ^("chan_" ++ p).asSymbol;
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
    { tt == \chan } {
        var slot = parts[1].asInteger - 1;
        var param = parts[2].asSymbol;
        [\chan, slot, param]
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

// Add/remove/set route
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
    
    ("Extended mod route added: bus % -> % [slot %]".format(sourceBus, targetStr, idx)).postln;
    
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

~setExtModUserParam = { |targetStr, value|
    ~extUserParams[targetStr] = value;
};

// Set target value (v1.7 - P1-P4 support via ~setModParam)
~setExtTargetValue = { |parsed, value|
    var targetType = parsed[0];
    var paramSym;
    
    case
    { targetType == \mod } {
        var slot = parsed[1];
        var param = parsed[2];
        
        // v1.7: P1-P4 use ~setModParam for type-aware mapping
        if(#[\p1, \p2, \p3, \p4].includes(param)) {
            // slot is already 1-indexed from target string (mod:1:p1 = M1)
            ~setModParam.(slot, param.asString, value);
            ^nil;
        };
        
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
            \type,   { \circuit },   // HEAT: type -> circuit
            \fbk,    { \feedback },  // ECHO: fbk -> feedback
            \spr,    { \spring },    // ECHO: spr -> spring  
            \siz,    { \size },      // REVERB: siz -> size
            \dec,    { \decay },     // REVERB: dec -> decay
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
    { targetType == \chan } {
        var slot = parsed[1];
        var param = parsed[2];
        
        if(~channelStrips[slot].notNil) {
            switch(param,
                \pan, { ~channelStrips[slot].set(\pan, value) }
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

// Apply modulation
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

"Extended modulation system loaded (v1.7 - P1-P4 cross-mod)".postln;
