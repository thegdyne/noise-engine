/*
Mod SauceOfGrav SynthDef (Phase B - v1)
4-output coupled physics modulator

Phase B additions:
- Overshoot detection: per-lane tracking of hubTarget crossings
- Hub impulses: overshoot events feed into hub velocity
- tanh smoothing: soft saturation instead of hard clip for hubBias

Reference: docs/SAUCE_OF_GRAV_SPEC_v1_4_3.md
*/

SynthDef(\ne_mod_sauce_of_grav, {
	arg out1, out2, out3, out4,
	    clockMode = 0,
	    rate = 0.5,
	    depth = 0.5,
	    gravity = 0.5,
	    resonance = 0.5,
	    excursion = 0.5,
	    calm = 0.5,
	    tension1 = 0.5, tension2 = 0.5, tension3 = 0.5, tension4 = 0.5,
	    mass1 = 0.5, mass2 = 0.5, mass3 = 0.5, mass4 = 0.5,
	    polarity1 = 0, polarity2 = 0, polarity3 = 0, polarity4 = 0,
	    clockTrigBus = 0,
	    clockIndex = 12,
	    bpmBus = 0;

	// === CONSTANTS (v1.4.3) ===
	var dt = ControlDur.ir;

	// Rate (refresh events)
	var rateDeadband = 0.05;
	var freeRateMin = 0.001;
	var freeRateMax = 100.0;

	// Mass
	var massBase = 0.25;
	var massGain = 2.1;

	// Coupling - with per-lane skew for symmetry breaking
	var hubCoupleGain = 6.0;
	var hubTensionExp = 0.70;
	var ringCoupleGain = 3.5;
	var ringTensionExp = 1.30;
	var ringSkewArr = #[0.012, 0.017, 0.014, 0.019];

	// Gravity
	var gravStiffGain = 6.0;

	// Excursion
	var excursionMin = 0.60;
	var excursionMax = 1.60;

	// Excursion -> hub travel shaping (Phase B)
    var excursionHubExp = 1.7;  // try 1.25..1.75 if you want to tune

	// CALM multipliers
	var calmDampCalm = 1.30;
	var calmDampWild = 0.75;
	var calmVdpCalm = 0.90;
	var calmVdpWild = 1.15;
	var calmKickCalm = 0.60;

	// Van der Pol
	var vdpInject = 0.8;
	var vdpThreshold = 0.35;
	var vdpHubMod = 0.05;
	var vdpThresholdFloor = 0.05;

	// Calibration trims
	var tensionTrim = #[0.012, -0.008, 0.015, -0.018];
	var massTrim = #[-0.010, 0.014, -0.006, 0.011];

	// Damping
	var dampingBase = 0.10;
	var dampingTension = 0.40;

	// Rails
	var railZone = 0.08;
	var railAbsorbBase = 0.35;

	// Resonance
	var resoFloorMin = 0.0002;
	var resoFloorMax = 0.0040;
	var resoDriveGain = 6.0;
	var resoDeltaEMax = 0.01;

	var resoDampAtLow = 0.75;  // 0.4..1.0 (higher = bigger R01 delta)


	// Kickstart
	var resoKickGain = 2.8;
	var resoKickMaxF = 0.30;
	var kickCooldownS = 0.20;

	// Hub (Phase B constants)
	var hubLimit = 2.0;
	var depthDampMin = 0.003;
	var depthDampMax = 2.35;
	var hubFeedGain = 8.0;
	var hubFeedMax = 0.35;
	var overshootToHubGain = 0.6;
	var overshootMax = 0.25;
	var velocityEpsilon = 0.001;
	var noiseRate = 0.012;

	// === STATE VARIABLES (Phase A: 13, Phase B adds 16 = 29 total) ===
	var pos1, pos2, pos3, pos4;
	var vel1, vel2, vel3, vel4;
	var hubBias, hubVel;
	var kickCooldown, kickToggle, kickIndex;

    // Phase B: Overshoot tracking state (16 values)
    var prevSide1, prevSide2, prevSide3, prevSide4;
    var osActive1, osActive2, osActive3, osActive4;
    var osTarget1, osTarget2, osTarget3, osTarget4;
    var osPeak1, osPeak2, osPeak3, osPeak4;

	// === WORKING VARIABLES ===
	var calmClamped, calmBi, tCalm, tWild, calmDampMul, calmVdpMul, calmKickMul;
	var gravInfluence, excursionGain, hubTarget;
	var kGrav, hubDamp;
	var mass, tensionEff, kHub, kRing, kRingFwd, kRingBwd, dampingBaseMapped;
	var vdpThresholdEff, amp, vdpFactor, dampingEff;
	var noise;
	var fGrav, fHub, fRing, fTotal;
	var eFloor, energy, fReso, fKick;
	var accel, railD, railU;
	var sig1, sig2, sig3, sig4;

	var didInit;
	var clk, atrig, trig, clockRunning, clkGate;
	var bpm, rateClamped, rateActive, baseHz, clkMult, refreshHz, refreshTrig, refreshPulse, fadeFactor;
	var railAbsorbEff, railZoneEff;

	// Phase B: Overshoot working variables
	var side1, side2, side3, side4;
	var didCross1, didCross2, didCross3, didCross4;
	var excursion1, excursion2, excursion3, excursion4;
	var velFlipped1, velFlipped2, velFlipped3, velFlipped4;
	var osImpulse1, osImpulse2, osImpulse3, osImpulse4;
	var hubImpulse, workSum, hubFeed;
    var excHubMul;
    var noiseRateEff, lowRateBoost;

	// === CLOCK INPUT ===
	clk = In.ar(clockTrigBus + clockIndex);
	atrig = Trig1.ar(clk > 0.5, 0.001);
	trig = Trig1.kr(A2K.kr(atrig), 0.001);
	bpm = In.kr(bpmBus).max(1);
	clockRunning = Decay.kr(trig, 0.2);
	clkGate = clockRunning.sign;

	// === CALM BIPOLAR CONVERSION ===
	calmClamped = calm.clip(0, 1);
	calmBi = (calmClamped * 2) - 1;
	tCalm = calmBi.neg.max(0);
	tWild = calmBi.max(0);
	calmDampMul = 1 + (tCalm * (calmDampCalm - 1)) + (tWild * (calmDampWild - 1));
	calmVdpMul  = 1 + (tCalm * (calmVdpCalm  - 1)) + (tWild * (calmVdpWild  - 1));
	calmKickMul = 1 + (tCalm * (calmKickCalm - 1));

	// === PARAMETER MAPPING ===
	gravInfluence = 1.0 - gravity;
	excursionGain = excursionMin + (excursion * (excursionMax - excursionMin));

	// === EXCURSION SCALING ===
	// excHubMul applies non-linear excursion shaping (power = excursionHubExp) with midpoint normalization.
	// hubTarget multiplies by (excursionGain ** excursionHubExp) again.
	// (Because hubTarget also multiplies by excursionGain ** excursionHubExp downstream.)
	// This is intentional: stronger response in the upper range without making low excursion feel dead.
	// With excursionHubExp=1.7, effective power ≈ 3.4.
    excHubMul =
        (excursionGain ** excursionHubExp) /
        (((excursionMin + excursionMax) * 0.5) ** excursionHubExp);
	kGrav = gravStiffGain * gravity;
	hubDamp = depthDampMin + (depth.clip(0,1) * (depthDampMax - depthDampMin));

	railZoneEff = (railZone * (1 - (0.35 * excursion))).clip(0.02, 0.12);
	railAbsorbEff = (railAbsorbBase * (1 - (0.50 * excursion))).clip(0.1, railAbsorbBase);

	mass = [
		massBase + (massGain * (mass1 + massTrim[0]).clip(0, 1)),
		massBase + (massGain * (mass2 + massTrim[1]).clip(0, 1)),
		massBase + (massGain * (mass3 + massTrim[2]).clip(0, 1)),
		massBase + (massGain * (mass4 + massTrim[3]).clip(0, 1))
	];

	tensionEff = [
		(tension1 + tensionTrim[0]).clip(0, 1),
		(tension2 + tensionTrim[1]).clip(0, 1),
		(tension3 + tensionTrim[2]).clip(0, 1),
		(tension4 + tensionTrim[3]).clip(0, 1)
	];

	kHub = hubCoupleGain * (tensionEff ** hubTensionExp);
	kRing = ringCoupleGain * (tensionEff ** ringTensionExp);
	kRingFwd = kRing * (1 + ringSkewArr);
	kRingBwd = kRing * (1 - ringSkewArr);

	dampingBaseMapped =
    (dampingBase + (dampingTension * (1 - tensionEff)))
    * calmDampMul
    * (1 + ((1 - resonance.clip(0, 1)) * resoDampAtLow));


	// === INIT WITH FEEDBACK (29 values) ===
    # pos1, pos2, pos3, pos4,
      vel1, vel2, vel3, vel4,
      hubBias, hubVel,
      kickCooldown, kickToggle, kickIndex,
      prevSide1, prevSide2, prevSide3, prevSide4,
      osActive1, osActive2, osActive3, osActive4,
      osTarget1, osTarget2, osTarget3, osTarget4,
      osPeak1, osPeak2, osPeak3, osPeak4 = LocalIn.kr(29);


	// sentinel: kickToggle only ever becomes +/-1
	didInit = kickToggle.abs > 0.001;

	pos1 = Select.kr(didInit, [0.5, pos1]);
	pos2 = Select.kr(didInit, [0.5, pos2]);
	pos3 = Select.kr(didInit, [0.5, pos3]);
	pos4 = Select.kr(didInit, [0.5, pos4]);

	vel1 = Select.kr(didInit, [0.0, vel1]);
	vel2 = Select.kr(didInit, [0.0, vel2]);
	vel3 = Select.kr(didInit, [0.0, vel3]);
	vel4 = Select.kr(didInit, [0.0, vel4]);

	hubBias = Select.kr(didInit, [0.0, hubBias]);
	hubVel  = Select.kr(didInit, [0.0, hubVel]);

	kickCooldown = Select.kr(didInit, [0.0, kickCooldown]);
	kickToggle   = Select.kr(didInit, [1.0, kickToggle]);
	kickIndex    = Select.kr(didInit, [0.0, kickIndex]);

	// Phase B init: overshoot tracking
	osActive1 = Select.kr(didInit, [0.0, osActive1]);
	osActive2 = Select.kr(didInit, [0.0, osActive2]);
	osActive3 = Select.kr(didInit, [0.0, osActive3]);
	osActive4 = Select.kr(didInit, [0.0, osActive4]);

	osTarget1 = Select.kr(didInit, [0.5, osTarget1]);
	osTarget2 = Select.kr(didInit, [0.5, osTarget2]);
	osTarget3 = Select.kr(didInit, [0.5, osTarget3]);
	osTarget4 = Select.kr(didInit, [0.5, osTarget4]);

	osPeak1 = Select.kr(didInit, [0.0, osPeak1]);
	osPeak2 = Select.kr(didInit, [0.0, osPeak2]);
	osPeak3 = Select.kr(didInit, [0.0, osPeak3]);
	osPeak4 = Select.kr(didInit, [0.0, osPeak4]);

	// === REFRESH EVENTS ===
	rateClamped = rate.clip(0, 1);
	rateActive = ((rateClamped - rateDeadband) / (1 - rateDeadband)).clip(0, 1);

	baseHz = bpm / 60;
	clkMult = Select.kr(
		(rateActive * 11).round.clip(0, 11),
		[1/64, 1/32, 1/16, 1/8, 1/4, 1/2, 1, 2, 4, 8, 16, 32]
	);

	refreshHz = rateActive.linexp(0, 1, freeRateMin, freeRateMax);

	refreshTrig = Select.kr(rateClamped < rateDeadband, [
		Select.kr(clockMode.round.clip(0, 1), [
			Impulse.kr(baseHz * clkMult) * clkGate,
			Impulse.kr(refreshHz)
		]),
		0
	]);

	refreshPulse = refreshTrig.sign;

	fadeFactor = 0.95 - (depth.clip(0,1) * 0.95);
	hubBias = hubBias * (1 + (refreshPulse * (fadeFactor - 1)));
	hubVel  = hubVel  * (1 + (refreshPulse * (fadeFactor - 1)));

	// === HUB TARGET ===
	hubTarget = (0.5 + (hubBias * gravInfluence * (excursionGain ** excursionHubExp) * excHubMul)).clip(0, 1);

	// === VAN DER POL DAMPING ===
	vdpThresholdEff = (vdpThreshold * (1 + (vdpHubMod * hubBias / hubLimit))).max(vdpThresholdFloor);
	amp = ([pos1, pos2, pos3, pos4] - 0.5).abs;
	vdpFactor = (vdpInject * calmVdpMul) * (1 - ((amp / vdpThresholdEff) ** 2));
	dampingEff = dampingBaseMapped - vdpFactor;

	// === VELOCITY NOISE ===
    // boost only when rate is low (< 0.2)
    lowRateBoost = ((0.2 - rateClamped) / 0.2).clip(0, 1);  // 0 at >=0.2, 0.5 at 0.1, 1 at 0
    noiseRateEff = noiseRate * (1 + (lowRateBoost * 0.9));  // was 0.6

    noise = [
        WhiteNoise.kr(noiseRateEff * 0.9) * dt.sqrt,
        WhiteNoise.kr(noiseRateEff * 1.1) * dt.sqrt,
        WhiteNoise.kr(noiseRateEff * 1.0) * dt.sqrt,
        WhiteNoise.kr(noiseRateEff * 1.2) * dt.sqrt
    ];
	vel1 = vel1 + noise[0];
	vel2 = vel2 + noise[1];
	vel3 = vel3 + noise[2];
	vel4 = vel4 + noise[3];

	// === FORCES ===
	fGrav = kGrav * (0.5 - [pos1, pos2, pos3, pos4]);
	fHub  = kHub  * (hubTarget - [pos1, pos2, pos3, pos4]);

	fRing = [
		(kRingFwd[0] * (pos2 - pos1)) + (kRingBwd[0] * (pos4 - pos1)),
		(kRingFwd[1] * (pos3 - pos2)) + (kRingBwd[1] * (pos1 - pos2)),
		(kRingFwd[2] * (pos4 - pos3)) + (kRingBwd[2] * (pos2 - pos3)),
		(kRingFwd[3] * (pos1 - pos4)) + (kRingBwd[3] * (pos3 - pos4))
	];

	// === RESONANCE ===
	eFloor = resoFloorMin + (resonance * (resoFloorMax - resoFloorMin));
	energy = 0.5 * ((mass[0] * vel1.squared) + (mass[1] * vel2.squared) +
	                (mass[2] * vel3.squared) + (mass[3] * vel4.squared));

	fReso = Select.kr(energy < eFloor, [
		[0, 0, 0, 0],
		resoDriveGain * resonance * (eFloor - energy).clip(0, resoDeltaEMax) * [vel1, vel2, vel3, vel4].sign
	]);

	// === KICKSTART ===
	kickCooldown = (kickCooldown - dt).max(0);

	fKick = Select.kr((energy < eFloor) * (kickCooldown < 0.001) * (resonance > 0.01), [
		[0, 0, 0, 0],
		resoKickGain * calmKickMul * (eFloor - energy).clip(0, resoKickMaxF) *
		kickToggle * [1, -1, 1, -1]
	]);

	kickCooldown = Select.kr((energy < eFloor) * (kickCooldown < 0.001) * (resonance > 0.01), [
		kickCooldown,
		kickCooldownS
	]);
	kickToggle = Select.kr((energy < eFloor) * (kickCooldown < 0.001) * (resonance > 0.01), [
		kickToggle,
		kickToggle.neg
	]);

	// === TOTAL FORCE & ACCELERATION ===
	fTotal = fGrav + fHub + fRing + fReso + fKick;
	accel = fTotal / mass;

	vel1 = vel1 + (accel[0] * dt);
	vel2 = vel2 + (accel[1] * dt);
	vel3 = vel3 + (accel[2] * dt);
	vel4 = vel4 + (accel[3] * dt);

	// === DAMPING ===
	vel1 = vel1 * (dampingEff[0] * dt).neg.exp;
	vel2 = vel2 * (dampingEff[1] * dt).neg.exp;
	vel3 = vel3 * (dampingEff[2] * dt).neg.exp;
	vel4 = vel4 * (dampingEff[3] * dt).neg.exp;

	// === INTEGRATE POSITION ===
	pos1 = pos1 + (vel1 * dt);
	pos2 = pos2 + (vel2 * dt);
	pos3 = pos3 + (vel3 * dt);
	pos4 = pos4 + (vel4 * dt);

	// === RAIL BUMPERS ===
	pos1 = pos1.clip(0, 1);
	pos2 = pos2.clip(0, 1);
	pos3 = pos3.clip(0, 1);
	pos4 = pos4.clip(0, 1);

	railD = [pos1, pos2, pos3, pos4].min(1 - [pos1, pos2, pos3, pos4]);
	railU = ((railZoneEff - railD) / railZoneEff).clip(0, 1);

	vel1 = vel1 * (1 - (railAbsorbEff * railU[0].squared));
	vel2 = vel2 * (1 - (railAbsorbEff * railU[1].squared));
	vel3 = vel3 * (1 - (railAbsorbEff * railU[2].squared));
	vel4 = vel4 * (1 - (railAbsorbEff * railU[3].squared));

    // === PHASE B: OVERSHOOT DETECTION (spec-correct) ===
    // side relative to clamped hubTarget
    side1 = (pos1 - hubTarget).sign;
    side2 = (pos2 - hubTarget).sign;
    side3 = (pos3 - hubTarget).sign;
    side4 = (pos4 - hubTarget).sign;

    // non-zero tests (UGen comparators)
    didCross1 =
        (side1.abs > 0) *
        (prevSide1.abs > 0) *
        ((side1 * prevSide1) < 0) *
        (vel1.abs > velocityEpsilon) *
        (osActive1 < 0.5);

    didCross2 =
        (side2.abs > 0) *
        (prevSide2.abs > 0) *
        ((side2 * prevSide2) < 0) *
        (vel2.abs > velocityEpsilon) *
        (osActive2 < 0.5);

    didCross3 =
        (side3.abs > 0) *
        (prevSide3.abs > 0) *
        ((side3 * prevSide3) < 0) *
        (vel3.abs > velocityEpsilon) *
        (osActive3 < 0.5);

    didCross4 =
        (side4.abs > 0) *
        (prevSide4.abs > 0) *
        ((side4 * prevSide4) < 0) *
        (vel4.abs > velocityEpsilon) *
        (osActive4 < 0.5);

    // latch target and activate on crossing
    osTarget1 = Select.kr(didCross1, [osTarget1, hubTarget]);
    osTarget2 = Select.kr(didCross2, [osTarget2, hubTarget]);
    osTarget3 = Select.kr(didCross3, [osTarget3, hubTarget]);
    osTarget4 = Select.kr(didCross4, [osTarget4, hubTarget]);

    osActive1 = Select.kr(didCross1, [osActive1, 1]);
    osActive2 = Select.kr(didCross2, [osActive2, 1]);
    osActive3 = Select.kr(didCross3, [osActive3, 1]);
    osActive4 = Select.kr(didCross4, [osActive4, 1]);

    // seed peak on crossing with current excursion (signed)
    osPeak1 = Select.kr(didCross1, [osPeak1, pos1 - osTarget1]);
    osPeak2 = Select.kr(didCross2, [osPeak2, pos2 - osTarget2]);
    osPeak3 = Select.kr(didCross3, [osPeak3, pos3 - osTarget3]);
    osPeak4 = Select.kr(didCross4, [osPeak4, pos4 - osTarget4]);

    // while active: track max |excursion| beyond frozen target
    excursion1 = pos1 - osTarget1;
    excursion2 = pos2 - osTarget2;
    excursion3 = pos3 - osTarget3;
    excursion4 = pos4 - osTarget4;

    osPeak1 = Select.kr((osActive1 > 0.5) * (excursion1.abs > osPeak1.abs), [osPeak1, excursion1]);
    osPeak2 = Select.kr((osActive2 > 0.5) * (excursion2.abs > osPeak2.abs), [osPeak2, excursion2]);
    osPeak3 = Select.kr((osActive3 > 0.5) * (excursion3.abs > osPeak3.abs), [osPeak3, excursion3]);
    osPeak4 = Select.kr((osActive4 > 0.5) * (excursion4.abs > osPeak4.abs), [osPeak4, excursion4]);

    // completion: velocity flips relative to excursion direction (spec)
    // done when (v * peak) < 0
    velFlipped1 = (osActive1 > 0.5) * ((vel1 * osPeak1) < 0);
    velFlipped2 = (osActive2 > 0.5) * ((vel2 * osPeak2) < 0);
    velFlipped3 = (osActive3 > 0.5) * ((vel3 * osPeak3) < 0);
    velFlipped4 = (osActive4 > 0.5) * ((vel4 * osPeak4) < 0);

    // impulse only on completion step
    osImpulse1 = velFlipped1 * osPeak1.clip(overshootMax.neg, overshootMax);
    osImpulse2 = velFlipped2 * osPeak2.clip(overshootMax.neg, overshootMax);
    osImpulse3 = velFlipped3 * osPeak3.clip(overshootMax.neg, overshootMax);
    osImpulse4 = velFlipped4 * osPeak4.clip(overshootMax.neg, overshootMax);

    // clear tracking on completion
    osActive1 = osActive1 * (1 - velFlipped1);
    osActive2 = osActive2 * (1 - velFlipped2);
    osActive3 = osActive3 * (1 - velFlipped3);
    osActive4 = osActive4 * (1 - velFlipped4);

    osPeak1 = osPeak1 * (1 - velFlipped1);
    osPeak2 = osPeak2 * (1 - velFlipped2);
    osPeak3 = osPeak3 * (1 - velFlipped3);
    osPeak4 = osPeak4 * (1 - velFlipped4);

    // update prevSide only if side != 0 (spec)
    prevSide1 = Select.kr(side1.abs > 0, [prevSide1, side1]);
    prevSide2 = Select.kr(side2.abs > 0, [prevSide2, side2]);
    prevSide3 = Select.kr(side3.abs > 0, [prevSide3, side3]);
    prevSide4 = Select.kr(side4.abs > 0, [prevSide4, side4]);



	// === HUB DYNAMICS (Phase B: impulses + tanh) ===
    hubImpulse = (overshootToHubGain * excHubMul)
        * (osImpulse1 + osImpulse2 + osImpulse3 + osImpulse4);

    workSum =
        ((pos1 - hubTarget) * vel1) + ((pos2 - hubTarget) * vel2) +
        ((pos3 - hubTarget) * vel3) + ((pos4 - hubTarget) * vel4);

    // raise the feed clip with excursion too (otherwise you just slam the clip sooner)
    hubFeed = (hubFeedGain * excHubMul * workSum)
        .clip((hubFeedMax * excHubMul).neg, (hubFeedMax * excHubMul));

	hubVel = hubVel + ((hubImpulse + hubFeed) * dt);
	hubVel = hubVel * (hubDamp * dt).neg.exp;
	hubBias = hubBias + (hubVel * dt);

	// Phase B: tanh soft saturation instead of clip
	hubBias = hubLimit * (hubBias / hubLimit).tanh;

	// === FEEDBACK STATE (29 values) ===
    LocalOut.kr([
        pos1, pos2, pos3, pos4,
        vel1, vel2, vel3, vel4,
        hubBias, hubVel,
        kickCooldown, kickToggle, kickIndex,
        prevSide1, prevSide2, prevSide3, prevSide4,
        osActive1, osActive2, osActive3, osActive4,
        osTarget1, osTarget2, osTarget3, osTarget4,
        osPeak1, osPeak2, osPeak3, osPeak4
    ]);


	// === OUTPUT WITH POLARITY ===
	sig1 = Select.kr(polarity1.round.clip(0, 1), [pos1, pos1.neg]);
	sig2 = Select.kr(polarity2.round.clip(0, 1), [pos2, pos2.neg]);
	sig3 = Select.kr(polarity3.round.clip(0, 1), [pos3, pos3.neg]);
	sig4 = Select.kr(polarity4.round.clip(0, 1), [pos4, pos4.neg]);

	Out.kr(out1, sig1);
	Out.kr(out2, sig2);
	Out.kr(out3, sig3);
	Out.kr(out4, sig4);
}).add;

"  ✓ ne_mod_sauce_of_grav SynthDef loaded (Phase B v1 - overshoot + tanh)".postln;
