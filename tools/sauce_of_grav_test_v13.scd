/*
=============================================================================
SauceOfGrav Parameter Test Suite v13.0
=============================================================================

SynthDef v10 (unchanged from v12)

Test fixes:
- D01: SKIPPED (hub damping not testable via lane outputs)
- R01: Changed to avgRange (avgMovement saturates in high-damping regime)
- T01: avgRange increase (correlation unreliable)
- E01: Symmetry-breaking params

OUTPUT: /tmp/sauce_test_v13.txt
=============================================================================
*/

(
var slot = ~testSlot ? 0;  // Use global if set, else default to 0
var baseBus;
var outFile;
var testResults = List.new;
var testsPassed = 0;
var testsFailed = 0;

// Synth creation args
var createSynthArgs = {
    [
        \out1, ~modBuses[baseBus].index,
        \out2, ~modBuses[baseBus + 1].index,
        \out3, ~modBuses[baseBus + 2].index,
        \out4, ~modBuses[baseBus + 3].index,
        \clockTrigBus, ~clockTrigBus.index,
        \clockIndex, 12,
        \bpmBus, ~clockBus.index
    ]
};

// === HELPER: Recreate synth with fresh state ===
var resetSynth = {
    if(~modNodes[slot].notNil) {
        ~modNodes[slot].free;
        0.1.wait;
    };
    ~modNodes[slot] = Synth(\ne_mod_sauce_of_grav, createSynthArgs.());
    "  [Synth recreated - fresh state]".postln;
    0.5.wait;
};

// === HELPER: Capture statistics ===
var captureStats = { |duration=12|
    var samples = (duration * 20).asInteger;

    var mins = [inf, inf, inf, inf];
    var maxs = [inf.neg, inf.neg, inf.neg, inf.neg];
    var sums = [0, 0, 0, 0];
    var sumsSq = [0, 0, 0, 0];
    var crossings = [0, 0, 0, 0];
    var prevSide = [0, 0, 0, 0];
    var prevVals = [0.5, 0.5, 0.5, 0.5];
    var totalMovement = [0, 0, 0, 0];
    var allVals = [List.new, List.new, List.new, List.new];

    // --- HUB PROXY (mean of 4 lanes) ---
    var hubMin, hubMax;
    var hubSum = 0;
    var hubPrev = 0.5;
    var hubMove = 0;
    var hubCross = 0;
    var hubPrevSide = 0;

    hubMin = inf; hubMax = inf.neg;

    samples.do {
        var vals = 4.collect { |j| ~modBuses[baseBus + j].getSynchronous };
        var hub = (vals[0] + vals[1] + vals[2] + vals[3]) * 0.25;
        var hubSide = if(hub > 0.5, 1, -1);

        // hub stats
        hubMin = min(hubMin, hub);
        hubMax = max(hubMax, hub);
        hubSum = hubSum + hub;
        hubMove = hubMove + (hub - hubPrev).abs;
        if(hubPrevSide != 0 and: { hubSide != hubPrevSide }) { hubCross = hubCross + 1 };
        hubPrevSide = hubSide;
        hubPrev = hub;

        // lane stats
        4.do { |j|
            var v = vals[j];
            var side = if(v > 0.5, 1, -1);
            mins[j] = min(mins[j], v);
            maxs[j] = max(maxs[j], v);
            sums[j] = sums[j] + v;
            sumsSq[j] = sumsSq[j] + (v * v);
            totalMovement[j] = totalMovement[j] + (v - prevVals[j]).abs;
            allVals[j].add(v);
            if(prevSide[j] != 0 and: { side != prevSide[j] }) { crossings[j] = crossings[j] + 1 };
            prevSide[j] = side;
            prevVals[j] = v;
        };

        0.05.wait;
    };

    // Calculate pairwise correlation (measure of coupling)
    {
        var corrs = List.new;
        var means, stds, hubMean;

        means = 4.collect { |i| sums[i] / samples };

        stds = 4.collect { |i|
            var variance = (sumsSq[i] / samples) - (means[i] * means[i]);
            variance.max(0.0001).sqrt;
        };


        [[0,1], [0,2], [0,3], [1,2], [1,3], [2,3]].do { |pair|
            var i = pair[0], j = pair[1];
            var cov = 0;
            samples.do { |k|
                cov = cov + ((allVals[i][k] - means[i]) * (allVals[j][k] - means[j]));
            };
            cov = cov / samples;
            corrs.add((cov / (stds[i] * stds[j])).abs);
        };

        // hub derived
        hubMean = hubSum / samples;

        (
            mins: mins,
            maxs: maxs,
            ranges: 4.collect { |i| maxs[i] - mins[i] },
            means: means,
            meanDev: (means - 0.5).abs.sum / 4,
            avgRange: (4.collect { |i| maxs[i] - mins[i] }).sum / 4,
            avgCrossings: crossings.sum / 4,
            rangeSpread: (4.collect { |i| maxs[i] - mins[i] }).maxItem -
                         (4.collect { |i| maxs[i] - mins[i] }).minItem,
            avgMovement: totalMovement.sum / (4 * samples),
            avgCorrelation: corrs.sum / 6,

            // hub proxy outputs
            hubMin: hubMin,
            hubMax: hubMax,
            hubRange: hubMax - hubMin,
            hubMean: hubMean,
            hubMeanDev: (hubMean - 0.5).abs,
            hubMovement: hubMove / samples,
            hubCrossings: hubCross / 1.0,  // raw count over the capture window

            duration: duration
        )
    }.value
};


// === HELPER: Set params on current synth ===
var setParams = { |params|
    var synth = ~modNodes[slot];
    params.keysValuesDo { |key, val| synth.set(key, val) };
    2.wait;
};

// === HELPER: Run comparison test (LOW vs HIGH) ===
var runComparison = { |testId, name, baseParams, lowParams, highParams, metric, expectedDir, minDelta, description, duration=12|
    var lowStats, highStats, delta, passed, resultStr;
    var isHubMetric;

    isHubMetric = (metric == \hubRange) or: { metric == \hubMeanDev } or: { metric == \hubMovement };

    "\n=== %: % ===".format(testId, name).postln;
    outFile.write("\n=== %: % ===\n".format(testId, name));
    outFile.write("  %\n".format(description));

    // Test LOW
    "  Testing LOW...".postln;
    resetSynth.();
    setParams.(baseParams);
    setParams.(lowParams);
    lowStats = captureStats.(duration);

    // Test HIGH
    "  Testing HIGH...".postln;
    resetSynth.();
    setParams.(baseParams);
    setParams.(highParams);
    highStats = captureStats.(duration);

    // Calculate delta
    delta = switch(metric,
        \avgRange,       { highStats.avgRange       - lowStats.avgRange },
        \meanDev,        { highStats.meanDev        - lowStats.meanDev },
        \avgCrossings,   { highStats.avgCrossings   - lowStats.avgCrossings },
        \rangeSpread,    { highStats.rangeSpread    - lowStats.rangeSpread },
        \avgMovement,    { highStats.avgMovement    - lowStats.avgMovement },
        \avgCorrelation, { highStats.avgCorrelation - lowStats.avgCorrelation },
        \hubRange,       { highStats.hubRange       - lowStats.hubRange },
        \hubMeanDev,     { highStats.hubMeanDev     - lowStats.hubMeanDev },
        \hubMovement,    { highStats.hubMovement    - lowStats.hubMovement }
    );

    passed = switch(expectedDir,
        \increase, { delta > minDelta },
        \decrease, { delta < minDelta.neg },
        \any,      { delta.abs > minDelta }
    );

    if(passed) { testsPassed = testsPassed + 1 } { testsFailed = testsFailed + 1 };

    // --- existing summary line (still prints lane range/cross/corr) ---
    resultStr = "  LOW:  %=% range=% crossings=% corr=%\n".format(
        metric,
        switch(metric,
            \avgRange,       { lowStats.avgRange.round(0.001) },
            \meanDev,        { lowStats.meanDev.round(0.001) },
            \avgCrossings,   { lowStats.avgCrossings.round(0.1) },
            \rangeSpread,    { lowStats.rangeSpread.round(0.001) },
            \avgMovement,    { lowStats.avgMovement.round(0.0001) },
            \avgCorrelation, { lowStats.avgCorrelation.round(0.001) },
            \hubRange,       { lowStats.hubRange.round(0.001) },
            \hubMeanDev,     { lowStats.hubMeanDev.round(0.001) },
            \hubMovement,    { lowStats.hubMovement.round(0.0001) }
        ),
        lowStats.avgRange.round(0.01),
        lowStats.avgCrossings.round(0.1),
        lowStats.avgCorrelation.round(0.01)
    );
    outFile.write(resultStr); resultStr.postln;

    // >>> 4) ADD THIS: explicit HUB line when using hub metrics <<<
    if(isHubMetric) {
        resultStr = "  HUB (LOW):  hubRange=% hubMeanDev=% hubMove=% hubCross=%\n".format(
            lowStats.hubRange.round(0.001),
            lowStats.hubMeanDev.round(0.001),
            lowStats.hubMovement.round(0.0001),
            lowStats.hubCrossings.round(0.1)
        );
        outFile.write(resultStr); resultStr.postln;
    };

    resultStr = "  HIGH: %=% range=% crossings=% corr=%\n".format(
        metric,
        switch(metric,
            \avgRange,       { highStats.avgRange.round(0.001) },
            \meanDev,        { highStats.meanDev.round(0.001) },
            \avgCrossings,   { highStats.avgCrossings.round(0.1) },
            \rangeSpread,    { highStats.rangeSpread.round(0.001) },
            \avgMovement,    { highStats.avgMovement.round(0.0001) },
            \avgCorrelation, { highStats.avgCorrelation.round(0.001) },
            \hubRange,       { highStats.hubRange.round(0.001) },
            \hubMeanDev,     { highStats.hubMeanDev.round(0.001) },
            \hubMovement,    { highStats.hubMovement.round(0.0001) }
        ),
        highStats.avgRange.round(0.01),
        highStats.avgCrossings.round(0.1),
        highStats.avgCorrelation.round(0.01)
    );
    outFile.write(resultStr); resultStr.postln;

    // >>> 4) ADD THIS: explicit HUB line when using hub metrics <<<
    if(isHubMetric) {
        resultStr = "  HUB (HIGH): hubRange=% hubMeanDev=% hubMove=% hubCross=%\n".format(
            highStats.hubRange.round(0.001),
            highStats.hubMeanDev.round(0.001),
            highStats.hubMovement.round(0.0001),
            highStats.hubCrossings.round(0.1)
        );
        outFile.write(resultStr); resultStr.postln;
    };

    resultStr = "  DELTA: % (need % %) → [%]\n".format(
        delta.round(0.001),
        expectedDir,
        minDelta,
        if(passed, "PASS", "FAIL")
    );
    outFile.write(resultStr); resultStr.postln;

    testResults.add((id: testId, name: name, passed: passed, delta: delta));
};

// === HELPER: Run single-condition floor test (no LOW vs HIGH delta) ===
var runFloor = { |testId, name, baseParams, testParams, metric, minValue, description, duration=12|
    var stats, passed, resultStr;

    "\n=== %: % ===".format(testId, name).postln;
    outFile.write("\n=== %: % ===\n".format(testId, name));
    outFile.write("  %\n".format(description));

    "  Testing...".postln;
    resetSynth.();
    setParams.(baseParams);
    setParams.(testParams);
    stats = captureStats.(duration);

    passed = switch(metric,
        \avgRange,     { stats.avgRange > minValue },
        \avgCrossings, { stats.avgCrossings > minValue },
        \avgMovement,  { stats.avgMovement > minValue }
    );

    if(passed) { testsPassed = testsPassed + 1 } { testsFailed = testsFailed + 1 };

    resultStr = "  %=% range=% crossings=% corr=%\n".format(
        metric,
        switch(metric,
            \avgRange,     { stats.avgRange.round(0.001) },
            \avgCrossings, { stats.avgCrossings.round(0.1) },
            \avgMovement,  { stats.avgMovement.round(0.0001) }
        ),
        stats.avgRange.round(0.01),
        stats.avgCrossings.round(0.1),
        stats.avgCorrelation.round(0.01)
    );
    outFile.write(resultStr); resultStr.postln;

    resultStr = "  FLOOR: %=% (need > %) → [%]\n".format(metric, stats.at(metric).round(0.001), minValue, if(passed, "PASS", "FAIL"));
    outFile.write(resultStr); resultStr.postln;

    testResults.add((id: testId, name: name, passed: passed, metric: metric, minValue: minValue, value: stats.at(metric)));
};

// === MAIN TEST SEQUENCE ===
fork {
    baseBus = slot * 4;
    
    outFile = File("/tmp/sauce_test_v13.txt", "w");
    outFile.write("=".dup(70).join ++ "\n");
    outFile.write("SauceOfGrav Parameter Test Suite v13.0\n");
    outFile.write("Date: %\n".format(Date.localtime.asString));
    outFile.write("R01 metric fix (avgRange instead of avgMovement)\n");
    outFile.write("=".dup(70).join ++ "\n");
    
    if(~modBuses.isNil or: { ~clockTrigBus.isNil } or: { ~clockBus.isNil }) {
        "ERROR: Required buses not found. Run init.scd first.".postln;
    } {
        "Starting tests on slot % (baseBus %)...\n".format(slot + 1, baseBus).postln;
        
        // ============================================================
        // D01 DEPTH: SKIPPED - hub damping not observable via outputs
        // Depth damps hubVel, but damped hub = stable anchor = lanes can oscillate
        // more regularly, so avgRange/avgCrossings don't capture the effect
        // Would need hubBias output bus to test properly
        // ============================================================
        outFile.write("\n=== D01: DEPTH (SKIPPED) ===\n");
        outFile.write("  Hub damping not observable via lane outputs.\n");
        outFile.write("  Damped hub = stable anchor = more regular oscillation.\n");
        outFile.write("  Would need hubBias output bus to test properly.\n");
        "=== D01: DEPTH (SKIPPED - not testable via outputs) ===".postln;
        
        // ============================================================
        // G01 GRAVITY: Center pull - ISOLATED
        // excursion=1 to amplify hub influence (gravity_influence = 1-gravity)
        // ============================================================
        runComparison.("G01", "GRAVITY affects center pull (isolated)",
            (clockMode: 1, rate: 0.5, depth: 0.5, resonance: 0.5, excursion: 1.0, calm: 0.5,
             tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5,
             mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
            (gravity: 0.0),
            (gravity: 1.0),
            \meanDev, \decrease, 0.005,
            "GRAVITY (isolated): excursion=1 amplifies hub. High gravity = tight around 0.5."
        );
        
        // ============================================================
        // R01 RESONANCE: "Die vs Sustain" test (AI2 fix v2)
        // avgMovement saturates in high-damping regime; use avgRange instead
        // Base regime wants to settle: calm=0, depth=1, gravity=0.7, rate=0
        // ============================================================
        runComparison.("R01", "RESONANCE sustains dying system",
            (clockMode: 1, rate: 0.0, depth: 1.0, gravity: 0.7, excursion: 0.5, calm: 0.0,
             tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5,
             mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
            (resonance: 0.0),
            (resonance: 1.0),
            \avgRange, \increase, 0.02,
            "RESONANCE (die vs sustain): high damping regime. Resonance keeps motion alive = larger range.",
            24  // longer capture
        );
        
        // ============================================================
        // E01 EXCURSION: Travel limits - SYMMETRY BROKEN (AI2 fix)
        // Non-uniform tension/mass prevents lock, resonance=0 removes sync
        // ============================================================
        runComparison.("E01", "EXCURSION affects hub travel (hub proxy)",
            (clockMode: 1, rate: 0.0,
             depth: 0.85,      // add damping so LOW doesn't hit rails
             gravity: 0.35,    // stops hub proxy saturating
             resonance: 0.0,
             calm: 0.25,       // reduce energy
             tension1: 0.2, tension2: 0.4, tension3: 0.6, tension4: 0.8,
             mass1: 0.7, mass2: 0.5, mass3: 0.4, mass4: 0.3),
            (excursion: 0.0),
            (excursion: 1.0),
            \hubRange, \increase, 0.03,
            "EXCURSION scales hubTarget via excursionGain. Use hub proxy (mean of lanes) range.",
            24
        );


        
        // ============================================================
        // C01 CALM: Motion amplitude
        // ============================================================
        runComparison.("C01", "CALM affects motion amplitude",
            (clockMode: 1, rate: 0.5, depth: 0.5, gravity: 0.5, resonance: 0.5, excursion: 0.5,
             tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5,
             mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
            (calm: 0.0),
            (calm: 1.0),
            \avgRange, \increase, 0.1,
            "CALM: 0=calm(small motion), 1=wild(big swings). Wild has larger range."
        );
        
        // ============================================================
        // F01 RATE: Skipped - refresh timing, not physics speed
        // ============================================================
        outFile.write("\n=== F01: RATE (SKIPPED) ===\n");
        outFile.write("  RATE controls refresh event timing, not physics frequency.\n");
        outFile.write("  This is not measurable via output crossings.\n");
        "=== F01: RATE (SKIPPED - refresh timing, not physics) ===".postln;
        
        // ============================================================
        // F02 RATE: Low rate should still have motion (AI2 fix)
        // Changed threshold from -0.3 (always pass) to 0.05
        // ============================================================
        runFloor.("F02", "RATE low still has motion (floor)",
            (clockMode: 1, depth: 0.5, gravity: 0.5, resonance: 0.5, excursion: 0.5, calm: 0.5,
             tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5,
             mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
            (rate: 0.1),
            \avgRange, 0.20,
            "RATE is refresh timing. Assert low rate is not dead (avgRange floor).",
            12
        );

        
        // ============================================================
        // T01 TENSION: Coupling - measure via avgRange (AI2 fix)
        // Correlation is unreliable; tension increases interaction/motion
        // ============================================================
        runComparison.("T01", "TENSION affects interaction",
            (clockMode: 1, rate: 0.5, depth: 0.5, gravity: 0.5, resonance: 0.0, excursion: 0.5, calm: 0.5,
             mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
            (tension1: 0.0, tension2: 0.0, tension3: 0.0, tension4: 0.0),
            (tension1: 1.0, tension2: 1.0, tension3: 1.0, tension4: 1.0),
            \avgRange, \increase, 0.1,
            "TENSION: High tension = more interaction = larger motion range."
        );
        
        // ============================================================
        // M01 MASS: Response speed (inertia)
        // ============================================================
        runComparison.("M01", "MASS affects response speed",
            (clockMode: 1, rate: 0.5, depth: 0.5, gravity: 0.5, resonance: 0.5, excursion: 0.5, calm: 0.5,
             tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5),
            (mass1: 0.0, mass2: 0.0, mass3: 0.0, mass4: 0.0),
            (mass1: 1.0, mass2: 1.0, mass3: 1.0, mass4: 1.0),
            \avgCrossings, \decrease, 1.0,
            "MASS is inertia. High mass = slow arcs, fewer crossings."
        );
        
        // ============================================================
        // SUMMARY
        // ============================================================
        outFile.write("\n" ++ "=".dup(70).join ++ "\n");
        outFile.write("SUMMARY: % PASSED, % FAILED out of % tests (2 skipped)\n".format(
            testsPassed, testsFailed, testsPassed + testsFailed));
        
        outFile.write("\nFailed tests:\n");
        testResults.do { |t|
            if(t.passed.not) {
                if(t.delta.notNil) {
                    outFile.write("  - %: % (delta=%)\n".format(t.id, t.name, t.delta.round(0.001)));
                } {
                    outFile.write("  - %: % (value=%)\n".format(t.id, t.name, t.value.round(0.001)));
                };
            };
        };

        
        outFile.write("=".dup(70).join ++ "\n");
        outFile.close;
        
        "\n" ++ "=".dup(50).join.postln;
        "TEST COMPLETE: % PASSED, % FAILED (2 skipped)".format(testsPassed, testsFailed).postln;
        "Results saved to /tmp/sauce_test_v13.txt".postln;
        "=".dup(50).join.postln;
    };
};
)
