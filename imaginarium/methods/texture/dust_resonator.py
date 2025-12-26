"""
imaginarium/methods/texture/dust_resonator.py
Dust impulses through resonant filter banks

Character: Organic, rain-like, crackling, natural
Tags: STOCH, texture, organic
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class DustResonatorTemplate(MethodTemplate):
    """Stochastic dust impulses exciting resonant filters."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="texture/dust_resonator",
            family="texture",
            display_name="Dust Resonator",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="dust_density",
                    min_val=0.5,
                    max_val=50.0,
                    default=8.0,
                    curve="exp",
                    label="DST",
                    tooltip="Impulse density (events per second)",
                    unit="e/s",
                ),
                ParamAxis(
                    name="ring_decay",
                    min_val=0.01,
                    max_val=2.0,
                    default=0.3,
                    curve="exp",
                    label="RNG",
                    tooltip="Resonator ring-out time",
                    unit="s",
                ),
                ParamAxis(
                    name="brightness",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.5,
                    curve="lin",
                    label="BRT",
                    tooltip="Resonator frequency range",
                    unit="",
                ),
                ParamAxis(
                    name="spread",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.4,
                    curve="lin",
                    label="SPR",
                    tooltip="Stereo spread of impulses",
                    unit="",
                ),
                ParamAxis(
                    name="crackle",
                    min_val=0.0,
                    max_val=1.0,
                    default=0.2,
                    curve="lin",
                    label="CRK",
                    tooltip="Additional crackle texture",
                    unit="",
                ),
            ],
            macro_controls=[
                MacroControl(
                    name="activity",
                    param_weights={
                        "dust_density": 1.0,
                        "crackle": 0.5,
                    },
                ),
                MacroControl(
                    name="sustain",
                    param_weights={
                        "ring_decay": 1.0,
                        "brightness": -0.3,
                    },
                ),
            ],
            default_tags={"topology": "stochastic", "character": "organic"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        tags = {
            "topology": "stochastic",
            "character": "organic",
            "family": "texture",
            "method": self._definition.method_id,
        }
        
        density = params.get("dust_density", 8)
        if density > 25:
            tags["density"] = "dense"
            tags["texture"] = "rain"
        elif density < 5:
            tags["density"] = "sparse"
            tags["texture"] = "drops"
        else:
            tags["density"] = "medium"
        
        decay = params.get("ring_decay", 0.3)
        if decay > 0.8:
            tags["resonance"] = "long"
        elif decay < 0.1:
            tags["resonance"] = "short"
        
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        # Get axes for sc_read_expr
        axes = {a.name: a for a in self._definition.param_axes}
        
        # Generate custom param read expressions
        density_read = axes["dust_density"].sc_read_expr("customBus0", 0)
        decay_read = axes["ring_decay"].sc_read_expr("customBus1", 1)
        brightness_read = axes["brightness"].sc_read_expr("customBus2", 2)
        spread_read = axes["spread"].sc_read_expr("customBus3", 3)
        crackle_read = axes["crackle"].sc_read_expr("customBus4", 4)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}, portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var dust_density, ring_decay, brightness, spread, crackle;
    var dustL, dustR, dustTrigL, dustTrigR;
    var resFreqL, resFreqR, resSigL, resSigR;
    var crackleSig;

    // Seed for determinism
    RandSeed.ir(1, seed);

    // Read standard params from buses
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
    amp = In.kr(~params[\\amplitude]);

    // === READ CUSTOM PARAMS ===
    {density_read}
    {decay_read}
    {brightness_read}
    {spread_read}
    {crackle_read}

    // === DUST IMPULSES ===
    // Separate L/R dust for stereo spread
    dustTrigL = Dust.ar(dust_density * (1 + (spread * 0.5)));
    dustTrigR = Dust.ar(dust_density * (1 + (spread * 0.5)));
    
    // When spread is 0, triggers are correlated
    dustTrigL = XFade2.ar(Dust.ar(dust_density), dustTrigL, spread * 2 - 1);
    dustTrigR = XFade2.ar(Dust.ar(dust_density), dustTrigR, spread * 2 - 1);
    
    // === RESONANT FILTERS ===
    // Frequency varies with brightness
    resFreqL = freq * TExpRand.ar(0.5, 2, dustTrigL) * (1 + (brightness * 2));
    resFreqR = freq * TExpRand.ar(0.5, 2, dustTrigR) * (1 + (brightness * 2));
    
    // Ringz resonator excited by dust
    resSigL = Ringz.ar(dustTrigL, resFreqL.clip(50, 12000), ring_decay);
    resSigR = Ringz.ar(dustTrigR, resFreqR.clip(50, 12000), ring_decay);
    
    // Add parallel resonators at harmonics
    resSigL = resSigL + (Ringz.ar(dustTrigL, (resFreqL * 2).clip(50, 12000), ring_decay * 0.7) * 0.3);
    resSigR = resSigR + (Ringz.ar(dustTrigR, (resFreqR * 2).clip(50, 12000), ring_decay * 0.7) * 0.3);
    
    // Add body resonance
    resSigL = resSigL + (Ringz.ar(dustTrigL, freq * 0.5, ring_decay * 1.5) * 0.2);
    resSigR = resSigR + (Ringz.ar(dustTrigR, freq * 0.5, ring_decay * 1.5) * 0.2);
    
    // === CRACKLE LAYER ===
    // Add vinyl/fire crackle texture
    crackleSig = Crackle.ar(1.8 + (crackle * 0.15)) * crackle * 0.15;
    crackleSig = crackleSig + (Dust2.ar(crackle * 30) * 0.1 * crackle);
    crackleSig = HPF.ar(crackleSig, 500);
    
    // === MIX ===
    sig = [resSigL + crackleSig, resSigR + crackleSig];
    
    // Soft limiting
    sig = sig.tanh;

    // === OUTPUT CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
