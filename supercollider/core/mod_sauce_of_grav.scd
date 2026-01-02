/*
Mod SauceOfGrav SynthDef
4-output coupled physics modulator inspired by Buchla 266 Source of Uncertainty

Physics simulation:
- Ring topology: outputs 1↔2↔3↔4↔1 with spring coupling
- Central hub: 2nd-order dynamics with momentum, accumulates directional bias
- Van der Pol damping: negative near center (energy injection), positive near rails
- RESO energy floor: prevents system starvation, includes kickstart
- Micro-asymmetries: per-node trims, non-reciprocal ring coupling

Controls:
- clockMode: CLK (refresh on clock) or FREE (continuous physics)
- rate: refresh/update rate
- depth: hub damping (drift persistence)
- gravity: restoring force to center + hub influence
- resonance: energy floor (RESO)
- excursion: output range/expressiveness
- calm: macro control (-1=calm, 0=neutral, +1=wild)

Per-output:
- tension1-4: coupling strength (hub + ring)
- mass1-4: inertia
- polarity1-4: NORM/INV

Reference: docs/SAUCE_OF_GRAV_SPEC_v1_4_3.md
*/

SynthDef(\ne_mod_sauce_of_grav, {
	arg out1, out2, out3, out4,           // 4 output bus indices
	    clockMode = 0,                     // 0=CLK, 1=FREE
	    rate = 0.5,                         // Rate control (0-1)
	    depth = 0.5,                        // Hub damping
	    gravity = 0.5,                      // Restoring force
	    resonance = 0.5,                    // Energy floor (RESO)
	    excursion = 0.5,                    // Range/expressiveness
	    calm = 0.5,                         // Macro: 0=calm, 0.5=neutral, 1=wild
	    // Per-output tension (coupling)
	    tension1 = 0.5, tension2 = 0.5, tension3 = 0.5, tension4 = 0.5,
	    // Per-output mass (inertia)
	    mass1 = 0.5, mass2 = 0.5, mass3 = 0.5, mass4 = 0.5,
	    // Per-output polarity (0=NORM, 1=INV)
	    polarity1 = 0, polarity2 = 0, polarity3 = 0, polarity4 = 0,
	    // Clock infrastructure
	    clockTrigBus = 0,
	    clockIndex = 12,
	    bpmBus = 0;

	// === CONSTANTS (v1.4.3) ===
	var dt = 1/400;  // Physics timestep (400 Hz)
	
	// Rate
	var rateDeadband = 0.05;
	var freeRateMin = 0.001;
	var freeRateMax = 100.0;
	
	// Mass
	var massBase = 0.25;
	var massGain = 2.1;
	
	// Coupling
	var hubCoupleGain = 6.0;
	var hubTensionExp = 0.70;
	var ringCoupleGain = 3.5;
	var ringTensionExp = 1.30;
	var ringSkew = 0.015;
	
	// Gravity
	var gravStiffGain = 6.0;
	
	// Excursion
	var excursionMin = 0.60;
	var excursionMax = 1.60;
	
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
	var railAbsorb = 0.35;
	
	// Resonance
	var resoFloorMin = 0.0002;
	var resoFloorMax = 0.0040;
	var resoDriveGain = 6.0;
	var resoDeltaEMax = 0.01;
	var resoRailExp = 1.4;
	
	// Kickstart
	var resoKickGain = 2.8;
	var resoKickMaxF = 0.30;
	var kickCooldownS = 0.20;
	
	// Hub
	var overshootToHubGain = 0.6;
	var overshootMax = 0.25;
	var hubLimit = 2.0;
	var depthDampMin = 0.005;
	var depthDampMax = 2.50;
	var hubFeedGain = 8.0;
	var hubFeedMax = 0.35;
	var noiseRate = 0.012;
	var velocityEpsilon = 0.001;
	
	// === STATE VARIABLES ===
	var pos1, pos2, pos3, pos4;           // Output positions (0-1)
	var vel1, vel2, vel3, vel4;           // Velocities
	var hubBias, hubVel;                   // Hub state
	var kickCooldown, kickToggle, kickIndex;
	
	// === WORKING VARIABLES ===
	var calmBi, calmDampMul, calmVdpMul, calmKickMul;
	var gravInfluence, excursionGain, hubTarget;
	var kGrav, hubDamp;
	var mass, tensionEff, kHub, kRing, kRingFwd, kRingBwd, dampingBaseMapped;
	var vdpThresholdEff, amp, vdpFactor, dampingEff;
	var noise;
	var fGrav, fHub, fRing, fTotal;
	var eFloor, energy, fReso, fKick;
	var accel, railD, railU;
	var sig1, sig2, sig3, sig4;
	var physicsRate, updateTrig;
	var clk, atrig, trig, bpm;
	
	// === CLOCK INPUT ===
	clk = In.ar(clockTrigBus + clockIndex);
	atrig = Trig1.ar(clk > 0.5, 0.001);
	trig = Trig1.kr(A2K.kr(atrig), 0.001);
	bpm = In.kr(bpmBus);
	
	// === PHYSICS UPDATE RATE ===
	// Rate 0-0.05 = OFF (hold), otherwise scale to physics rate
	// Select.kr: index 0 = false (rate >= deadband), index 1 = true (rate < deadband)
	physicsRate = Select.kr(rate < rateDeadband, [
		rate.linexp(rateDeadband, 1.0, 1.0, 400.0),  // Active: scale rate
		0  // OFF (rate below deadband)
	]);
	
	// Update trigger - drives physics at variable rate
	updateTrig = Impulse.kr(physicsRate);
	
	// === CALM BIPOLAR CONVERSION ===
	// calm input is 0-1, convert to bipolar -1..+1
	calmBi = (calm * 2) - 1;
	
	// === CALM MULTIPLIERS ===
	// Select.kr: index 0 = false (calmBi >= 0, wild), index 1 = true (calmBi < 0, calm)
	calmDampMul = Select.kr(calmBi < 0, [
		1.0.blend(calmDampWild, calmBi),      // Wild (calmBi >= 0)
		1.0.blend(calmDampCalm, calmBi.neg)   // Calm (calmBi < 0)
	]);
	calmVdpMul = Select.kr(calmBi < 0, [
		1.0.blend(calmVdpWild, calmBi),       // Wild
		1.0.blend(calmVdpCalm, calmBi.neg)    // Calm
	]);
	calmKickMul = Select.kr(calmBi < 0, [
		1.0,                                   // Wild: no change
		1.0.blend(calmKickCalm, calmBi.neg)   // Calm: reduce kick
	]);
	
	// === PARAMETER MAPPING ===
	gravInfluence = 1.0 - gravity;
	excursionGain = excursionMin + (excursion * (excursionMax - excursionMin));
	kGrav = gravStiffGain * gravity;
	hubDamp = depthDampMin + (depth * (depthDampMax - depthDampMin));
	
	// Per-output mass with trims
	mass = [
		massBase + (massGain * (mass1 + massTrim[0]).clip(0, 1)),
		massBase + (massGain * (mass2 + massTrim[1]).clip(0, 1)),
		massBase + (massGain * (mass3 + massTrim[2]).clip(0, 1)),
		massBase + (massGain * (mass4 + massTrim[3]).clip(0, 1))
	];
	
	// Per-output tension with trims
	tensionEff = [
		(tension1 + tensionTrim[0]).clip(0, 1),
		(tension2 + tensionTrim[1]).clip(0, 1),
		(tension3 + tensionTrim[2]).clip(0, 1),
		(tension4 + tensionTrim[3]).clip(0, 1)
	];
	
	// Coupling constants
	kHub = hubCoupleGain * (tensionEff ** hubTensionExp);
	kRing = ringCoupleGain * (tensionEff ** ringTensionExp);
	kRingFwd = kRing * (1 + ringSkew);  // Forward neighbor (i+1)
	kRingBwd = kRing * (1 - ringSkew);  // Backward neighbor (i-1)
	
	// Base damping
	dampingBaseMapped = (dampingBase + (dampingTension * (1 - tensionEff))) * calmDampMul;
	
	// === INITIALIZE STATE WITH FEEDBACK ===
	// LocalIn provides previous frame's state
	// Order: pos1-4, vel1-4, hubBias, hubVel, kickCooldown, kickToggle, kickIndex
	# pos1, pos2, pos3, pos4, vel1, vel2, vel3, vel4, 
	  hubBias, hubVel, kickCooldown, kickToggle, kickIndex = LocalIn.kr(13);
	
	// Initialize on first sample (when all zeros)
	// Check sum BEFORE modifying any position
	// Select.kr: index 0 = condition false, index 1 = condition true
	pos1 = Select.kr(pos1.abs + pos2.abs + pos3.abs + pos4.abs > 0.001, [0.5, pos1]);
	pos2 = Select.kr(pos1.abs + pos2.abs + pos3.abs + pos4.abs > 0.001, [0.5, pos2]);
	pos3 = Select.kr(pos1.abs + pos2.abs + pos3.abs + pos4.abs > 0.001, [0.5, pos3]);
	pos4 = Select.kr(pos1.abs + pos2.abs + pos3.abs + pos4.abs > 0.001, [0.5, pos4]);
	kickToggle = Select.kr(kickToggle.abs > 0.001, [1, kickToggle]);
	
	// === HUB TARGET ===
	hubTarget = (0.5 + (hubBias * gravInfluence * excursionGain)).clip(0, 1);
	
	// === VAN DER POL DAMPING ===
	vdpThresholdEff = (vdpThreshold * (1 + (vdpHubMod * hubBias / hubLimit))).max(vdpThresholdFloor);
	amp = [pos1, pos2, pos3, pos4] - 0.5;
	amp = amp.abs;
	vdpFactor = (vdpInject * calmVdpMul) * (1 - ((amp / vdpThresholdEff) ** 2));
	dampingEff = dampingBaseMapped - vdpFactor;
	
	// === VELOCITY NOISE ===
	noise = [
		WhiteNoise.kr(noiseRate * dt.sqrt),
		WhiteNoise.kr(noiseRate * dt.sqrt),
		WhiteNoise.kr(noiseRate * dt.sqrt),
		WhiteNoise.kr(noiseRate * dt.sqrt)
	];
	vel1 = vel1 + (noise[0] * updateTrig);
	vel2 = vel2 + (noise[1] * updateTrig);
	vel3 = vel3 + (noise[2] * updateTrig);
	vel4 = vel4 + (noise[3] * updateTrig);
	
	// === FORCES ===
	// Gravity (restoring to center)
	fGrav = kGrav * (0.5 - [pos1, pos2, pos3, pos4]);
	
	// Hub coupling (attraction to hub target)
	fHub = kHub * (hubTarget - [pos1, pos2, pos3, pos4]);
	
	// Ring coupling (non-reciprocal: neighbors pull differently)
	// Ring: 1↔2↔3↔4↔1
	fRing = [
		(kRingFwd[0] * (pos2 - pos1)) + (kRingBwd[0] * (pos4 - pos1)),  // Node 1: next=2, prev=4
		(kRingFwd[1] * (pos3 - pos2)) + (kRingBwd[1] * (pos1 - pos2)),  // Node 2: next=3, prev=1
		(kRingFwd[2] * (pos4 - pos3)) + (kRingBwd[2] * (pos2 - pos3)),  // Node 3: next=4, prev=2
		(kRingFwd[3] * (pos1 - pos4)) + (kRingBwd[3] * (pos3 - pos4))   // Node 4: next=1, prev=3
	];
	
	// === RESONANCE ENERGY FLOOR ===
	eFloor = resoFloorMin + (resonance * (resoFloorMax - resoFloorMin));
	energy = 0.5 * ((mass[0] * vel1.squared) + (mass[1] * vel2.squared) + 
	                (mass[2] * vel3.squared) + (mass[3] * vel4.squared));
	
	// Simple resonance drive when energy below floor
	// Select.kr: index 0 = false (energy >= eFloor), index 1 = true (energy < eFloor)
	fReso = Select.kr(energy < eFloor, [
		[0, 0, 0, 0],  // No drive needed
		resoDriveGain * resonance * (eFloor - energy).clip(0, resoDeltaEMax) * [vel1, vel2, vel3, vel4].sign
	]);
	
	// === KICKSTART (simplified) ===
	// Decrement cooldown
	kickCooldown = (kickCooldown - (dt * updateTrig)).max(0);
	
	// Kick condition: energy low AND cooldown expired AND resonance active
	// Store condition to avoid re-evaluation
	// Note: in SC, boolean multiplication gives 0 or 1
	fKick = Select.kr((energy < eFloor) * (kickCooldown < 0.001) * (resonance > 0.01), [
		[0, 0, 0, 0],  // No kick
		resoKickGain * calmKickMul * (eFloor - energy).clip(0, resoKickMaxF) * 
		kickToggle * [1, -1, 1, -1]  // Alternating pattern
	]);
	
	// Reset cooldown and flip toggle when kick fires
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
	
	// Apply acceleration (only when update triggered)
	vel1 = vel1 + (accel[0] * dt * updateTrig);
	vel2 = vel2 + (accel[1] * dt * updateTrig);
	vel3 = vel3 + (accel[2] * dt * updateTrig);
	vel4 = vel4 + (accel[3] * dt * updateTrig);
	
	// === DAMPING (exponential decay) ===
	// Python: vel *= exp(-damping * dt)
	// Approximation for small dt: exp(-x) ≈ 1-x, but we use proper exp
	vel1 = vel1 * (dampingEff[0] * dt * updateTrig).neg.exp;
	vel2 = vel2 * (dampingEff[1] * dt * updateTrig).neg.exp;
	vel3 = vel3 * (dampingEff[2] * dt * updateTrig).neg.exp;
	vel4 = vel4 * (dampingEff[3] * dt * updateTrig).neg.exp;
	
	// === INTEGRATE POSITION ===
	pos1 = pos1 + (vel1 * dt * updateTrig);
	pos2 = pos2 + (vel2 * dt * updateTrig);
	pos3 = pos3 + (vel3 * dt * updateTrig);
	pos4 = pos4 + (vel4 * dt * updateTrig);
	
	// === RAIL BUMPERS ===
	// Soft collision at 0 and 1
	pos1 = pos1.clip(0, 1);
	pos2 = pos2.clip(0, 1);
	pos3 = pos3.clip(0, 1);
	pos4 = pos4.clip(0, 1);
	
	// Absorb velocity near rails
	railD = [pos1, pos2, pos3, pos4].min(1 - [pos1, pos2, pos3, pos4]);
	railU = ((railZone - railD) / railZone).clip(0, 1);
	vel1 = vel1 * (1 - (railAbsorb * railU[0].squared));
	vel2 = vel2 * (1 - (railAbsorb * railU[1].squared));
	vel3 = vel3 * (1 - (railAbsorb * railU[2].squared));
	vel4 = vel4 * (1 - (railAbsorb * railU[3].squared));
	
	// === HUB DYNAMICS (simplified) ===
	// Hub accumulates work from output motion
	hubVel = hubVel + (hubFeedGain * ((pos1 - hubTarget) * vel1 + (pos2 - hubTarget) * vel2 +
	                                   (pos3 - hubTarget) * vel3 + (pos4 - hubTarget) * vel4).clip(hubFeedMax.neg, hubFeedMax) * dt * updateTrig);
	hubVel = hubVel * (hubDamp * dt * updateTrig).neg.exp;  // Exponential decay
	hubBias = hubBias + (hubVel * dt * updateTrig);
	hubBias = hubBias.clip(hubLimit.neg, hubLimit);
	
	// === FEEDBACK STATE ===
	LocalOut.kr([pos1, pos2, pos3, pos4, vel1, vel2, vel3, vel4,
	             hubBias, hubVel, kickCooldown, kickToggle, kickIndex]);
	
	// === OUTPUT WITH POLARITY ===
	sig1 = Select.kr(polarity1.round, [pos1, 1 - pos1]);
	sig2 = Select.kr(polarity2.round, [pos2, 1 - pos2]);
	sig3 = Select.kr(polarity3.round, [pos3, 1 - pos3]);
	sig4 = Select.kr(polarity4.round, [pos4, 1 - pos4]);
	
	// === OUTPUT TO BUSES ===
	Out.kr(out1, sig1);
	Out.kr(out2, sig2);
	Out.kr(out3, sig3);
	Out.kr(out4, sig4);
}).add;

"  ✓ ne_mod_sauce_of_grav SynthDef loaded (4-output coupled physics)".postln;
