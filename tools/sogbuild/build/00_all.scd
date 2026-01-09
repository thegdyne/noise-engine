/*
Mod SauceOfGrav SynthDef v2.0 - Hub Mass Model
4-output coupled physics modulator

v2 changes:
- hubPos/hubVel: physical hub position (replaces hubBias/hubTarget semantics)
- Mass: weights hub attraction (heavier pillar pulls hub harder)
- Tension: spring stiffness (how tightly pillar follows hub) + ring coupling
- Gravity: master coupling strength
- Removed: fixed 0.5 attractor, separate fHub

Reference: SAUCE_OF_GRAV_V2_SPEC.md
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
	    globalTension = -1,
	    globalPolarity = -1,
	    clockTrigBus = 0,
	    clockIndex = 12,
	    bpmBus = 0;

	// === CONSTANTS ===
	var dt = ControlDur.ir;

	// Rate
	var rateMinMul   = 0.001;
	var rateCurveExp = 0.2;
	var dtStepMaxMul = 0.95;

	// Clock
	var bpmRef       = 120.0;
	var bpmMaxMul    = 4.0;

	// Mass (for pillar inertia)
	var massBase = 0.25;
	var massGain = 2.1;

	// Hub physics (v2)
	var hubMass = 1.0;
	var hubDampBase = 0.5;
	var hubDampGain = 4.0;
	var hubPullGain = 8.0;      // how strongly pillars pull hub
	var hubLimit = 0.9;         // soft limit for hub position

	// Spring coupling (gravity * tension)
	var springGain = 6.0;
	var springExp = 0.8;

	// Ring coupling
	var ringCoupleGain = 3.5;
	var ringTensionExp = 1.30;
	var ringSkewArr = #[0.012, 0.017, 0.014, 0.019];

	// CALM
	var calmDampCalm = 1.30;
	var calmDampWild = 0.75;
	var calmVdpCalm = 0.90;
	var calmVdpWild = 1.15;
	var calmKickCalm = 0.60;

	// Van der Pol
	var vdpInject = 0.8;
	var vdpThreshold = 0.35;
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
	var resoDampAtLow = 0.75;

	// Kickstart
	var resoKickGain = 2.8;
	var resoKickMaxF = 0.30;
	var kickCooldownS = 0.20;

	// Noise
	var noiseRate = 0.012;

	// === STATE VARIABLES (v2: 15 values) ===
	var pos1, pos2, pos3, pos4;
	var vel1, vel2, vel3, vel4;
	var hubPos, hubVel;
	var kickCooldown, kickToggle, kickIndex;
	// removed: hubBias, hubVel (old), overshoot tracking (16 values)
	// v2 is simpler: hub physics replaces overshoot system

	// === WORKING VARIABLES ===
	var calmClamped, calmBi, tCalm, tWild, calmDampMul, calmVdpMul, calmKickMul;
	var mass, tensionEff, kSpring, kRing, kRingFwd, kRingBwd, dampingBaseMapped;
	var vdpThresholdEff, amp, vdpFactor, dampingEff;
	var noise;
	var fToHub, fRing, fTotal;
	var eFloor, energy, fReso, fKick;
	var accel, railD, railU;
	var sig1, sig2, sig3, sig4;

	var didInit;
	var clk, atrig, trig, clockRunning, clkGate;
	var bpm, rateClamped, rateActive, baseHz, clkMult, dtStep;
	var railAbsorbEff, railZoneEff;
	var lowRateBoost, noiseRateEff;

	// Hub working variables (v2)
	var massWeight, displacement, fHubFromPillars, fHubDamp, hubAccel, hubDampCoeff;

	// Global override variables
	var gTens, gPol;
	var effTens1, effTens2, effTens3, effTens4;
	var effPol1, effPol2, effPol3, effPol4;

	// === GLOBAL OVERRIDES ===
	gTens = globalTension.clip(0, 1);
	gPol = globalPolarity.clip(0, 1).round(1);

	effTens1 = Select.kr(globalTension >= 0, [tension1.clip(0, 1), gTens]);
	effTens2 = Select.kr(globalTension >= 0, [tension2.clip(0, 1), gTens]);
	effTens3 = Select.kr(globalTension >= 0, [tension3.clip(0, 1), gTens]);
	effTens4 = Select.kr(globalTension >= 0, [tension4.clip(0, 1), gTens]);

	effPol1 = Select.kr(globalPolarity >= 0, [polarity1.clip(0, 1).round(1), gPol]);
	effPol2 = Select.kr(globalPolarity >= 0, [polarity2.clip(0, 1).round(1), gPol]);
	effPol3 = Select.kr(globalPolarity >= 0, [polarity3.clip(0, 1).round(1), gPol]);
	effPol4 = Select.kr(globalPolarity >= 0, [polarity4.clip(0, 1).round(1), gPol]);

	// === CLOCK INPUT ===
	clk = In.ar(clockTrigBus + clockIndex);
	atrig = Trig1.ar(clk > 0.5, ControlDur.ir * 2);
	trig = Trig1.kr(A2K.kr(atrig), ControlDur.ir * 2);
	bpm = In.kr(bpmBus).max(1);
	clockRunning = Decay.kr(trig, 0.2);
	clkGate = clockRunning.sign;

	// === CALM ===
	calmClamped = calm.clip(0, 1);
	calmBi = (calmClamped * 2) - 1;
	tCalm = calmBi.neg.max(0);
	tWild = calmBi.max(0);
	calmDampMul = 1 + (tCalm * (calmDampCalm - 1)) + (tWild * (calmDampWild - 1));
	calmVdpMul  = 1 + (tCalm * (calmVdpCalm  - 1)) + (tWild * (calmVdpWild  - 1));
	calmKickMul = 1 + (tCalm * (calmKickCalm - 1));

	// === PARAMETER MAPPING ===

	// Hub damping from depth
	hubDampCoeff = hubDampBase + (depth.clip(0, 1) * hubDampGain);

	// Rail zone from excursion
	railZoneEff = (railZone * (1 - (0.35 * excursion))).clip(0.02, 0.12);
	railAbsorbEff = (railAbsorbBase * (1 - (0.50 * excursion))).clip(0.1, railAbsorbBase);

	// Pillar mass (for inertia)
	mass = [
		massBase + (massGain * (mass1 + massTrim[0]).clip(0, 1)),
		massBase + (massGain * (mass2 + massTrim[1]).clip(0, 1)),
		massBase + (massGain * (mass3 + massTrim[2]).clip(0, 1)),
		massBase + (massGain * (mass4 + massTrim[3]).clip(0, 1))
	];

	// Mass weights for hub attraction (normalized so mean = 1)
	massWeight = mass / (mass.sum * 0.25);

	// Tension with trims
	tensionEff = [
		(effTens1 + tensionTrim[0]).clip(0, 1),
		(effTens2 + tensionTrim[1]).clip(0, 1),
		(effTens3 + tensionTrim[2]).clip(0, 1),
		(effTens4 + tensionTrim[3]).clip(0, 1)
	];

	// Spring stiffness (pillar↔hub) from gravity * tension
	kSpring = gravity * springGain * (tensionEff ** springExp);

	// Ring coupling (unchanged)
	kRing = ringCoupleGain * (tensionEff ** ringTensionExp);
	kRingFwd = kRing * (1 + ringSkewArr);
	kRingBwd = kRing * (1 - ringSkewArr);

	// Base damping
	dampingBaseMapped =
		(dampingBase + (dampingTension * (1 - tensionEff)))
		* calmDampMul
		* (1 + ((1 - resonance.clip(0, 1)) * resoDampAtLow));

	// === INIT WITH FEEDBACK (v2: 15 values) ===
	# pos1, pos2, pos3, pos4,
	  vel1, vel2, vel3, vel4,
	  hubPos, hubVel,
	  kickCooldown, kickToggle, kickIndex = LocalIn.kr(13);

	// Sentinel: kickToggle only ever becomes +/-1
	didInit = kickToggle.abs > 0.001;

	pos1 = Select.kr(didInit, [0.5, pos1]);
	pos2 = Select.kr(didInit, [0.5, pos2]);
	pos3 = Select.kr(didInit, [0.5, pos3]);
	pos4 = Select.kr(didInit, [0.5, pos4]);

	vel1 = Select.kr(didInit, [0.0, vel1]);
	vel2 = Select.kr(didInit, [0.0, vel2]);
	vel3 = Select.kr(didInit, [0.0, vel3]);
	vel4 = Select.kr(didInit, [0.0, vel4]);

	hubPos = Select.kr(didInit, [0.5, hubPos]);
	hubVel = Select.kr(didInit, [0.0, hubVel]);

	kickCooldown = Select.kr(didInit, [0.0, kickCooldown]);
	kickToggle   = Select.kr(didInit, [1.0, kickToggle]);
	kickIndex    = Select.kr(didInit, [0, kickIndex]);

	// === RATE / CLOCK TIMESCALE ===
	rateClamped = rate.clip(0, 1);
	baseHz = rateClamped.pow(rateCurveExp);
	rateActive = baseHz.linexp(0, 1, rateMinMul, 1.0);

	clkMult = Select.kr(clockMode.round.clip(0, 1), [
		((bpm / bpmRef).clip(0, bpmMaxMul)) * clkGate,
		1.0
	]);

	dtStep = (dt * rateActive * clkMult).clip(0, dt * dtStepMaxMul);

	// === VAN DER POL THRESHOLD ===
	vdpThresholdEff = vdpThreshold.max(vdpThresholdFloor);
	amp = ([pos1, pos2, pos3, pos4] - 0.5).abs;
	vdpFactor = (vdpInject * calmVdpMul) * (1 - ((amp / vdpThresholdEff) ** 2));
	dampingEff = dampingBaseMapped - vdpFactor;

	// === VELOCITY NOISE ===
	lowRateBoost = ((0.2 - rateClamped) / 0.2).clip(0, 1);
	noiseRateEff = noiseRate * (1 + (lowRateBoost * 0.9));

	noise = [
		WhiteNoise.kr(noiseRateEff * 0.9) * dtStep.sqrt,
		WhiteNoise.kr(noiseRateEff * 1.1) * dtStep.sqrt,
		WhiteNoise.kr(noiseRateEff * 1.0) * dtStep.sqrt,
		WhiteNoise.kr(noiseRateEff * 1.2) * dtStep.sqrt
	];
	vel1 = vel1 + noise[0];
	vel2 = vel2 + noise[1];
	vel3 = vel3 + noise[2];
	vel4 = vel4 + noise[3];

	// === HUB PHYSICS (v2) ===
	// Displacement: pillar position relative to hub
	displacement = [pos1, pos2, pos3, pos4] - hubPos;

	// Force on hub from pillars (mass-weighted spring pulls)
	// Heavier pillar pulls hub harder toward it
	fHubFromPillars = hubPullGain * gravity * (massWeight * displacement).sum;

	// Hub damping
	fHubDamp = hubVel.neg * hubDampCoeff;

	// Hub acceleration and integration
	hubAccel = (fHubFromPillars + fHubDamp) / hubMass;
	hubVel = hubVel + (hubAccel * dtStep);
	hubPos = hubPos + (hubVel * dtStep);

	// Soft limit hub to stay bounded (tanh saturation)
	hubPos = 0.5 + (hubLimit * ((hubPos - 0.5) / hubLimit).tanh);

	// === FORCES ON PILLARS ===

	// Spring pull toward hub (replaces old fGrav to 0.5 + fHub)
	fToHub = kSpring * (hubPos - [pos1, pos2, pos3, pos4]);

	// Ring coupling (unchanged)
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
	kickCooldown = (kickCooldown - dtStep).max(0);

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
	fTotal = fToHub + fRing + fReso + fKick;
	accel = fTotal / mass;

	vel1 = vel1 + (accel[0] * dtStep);
	vel2 = vel2 + (accel[1] * dtStep);
	vel3 = vel3 + (accel[2] * dtStep);
	vel4 = vel4 + (accel[3] * dtStep);

	// === DAMPING ===
	vel1 = vel1 * (dampingEff[0] * dtStep).neg.exp;
	vel2 = vel2 * (dampingEff[1] * dtStep).neg.exp;
	vel3 = vel3 * (dampingEff[2] * dtStep).neg.exp;
	vel4 = vel4 * (dampingEff[3] * dtStep).neg.exp;

	// === INTEGRATE POSITION ===
	pos1 = pos1 + (vel1 * dtStep);
	pos2 = pos2 + (vel2 * dtStep);
	pos3 = pos3 + (vel3 * dtStep);
	pos4 = pos4 + (vel4 * dtStep);

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

	// === FEEDBACK STATE (v2: 13 values) ===
	LocalOut.kr([
		pos1, pos2, pos3, pos4,
		vel1, vel2, vel3, vel4,
		hubPos, hubVel,
		kickCooldown, kickToggle, kickIndex
	]);

	// === OUTPUT WITH POLARITY ===
	sig1 = Select.kr(effPol1, [pos1, pos1.neg]);
	sig2 = Select.kr(effPol2, [pos2, pos2.neg]);
	sig3 = Select.kr(effPol3, [pos3, pos3.neg]);
	sig4 = Select.kr(effPol4, [pos4, pos4.neg]);

	Out.kr(out1, sig1);
	Out.kr(out2, sig2);
	Out.kr(out3, sig3);
	Out.kr(out4, sig4);
}).add;

"  ✓ ne_mod_sauce_of_grav SynthDef loaded (v2.0 - hub mass model)".postln;
