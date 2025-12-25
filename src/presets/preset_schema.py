"""
Preset schema definition and validation.
v2 - Phase 1: Channel strip expansion (EQ, gain, sends, cuts)
   - Phase 2: BPM + Master section (EQ, compressor, limiter)
   - Phase 3: Modulation sources (4 slots × 4 outputs)
   - Phase 4: Modulation routing (connections)
   - Phase 5: FX state (Heat, Echo, Reverb, Dual Filter)
"""

from dataclasses import dataclass, field
from typing import Optional
import json

PRESET_VERSION = 2
MAPPING_VERSION = 1  # For future UI→value curve changes

# Valid ranges
FILTER_TYPES = 6      # 0=LP, 1=HP, 2=BP, 3=Notch, 4=LP2, 5=OFF
ENV_SOURCES = 3       # 0=OFF, 1=CLK, 2=MIDI  
CLOCK_RATES = 13      # 0-12
MIDI_CHANNELS = 16    # 0-16 (0=OFF)
NUM_SLOTS = 8
NUM_CUSTOM_PARAMS = 5
GAIN_STAGES = 3       # 0=0dB, 1=+6dB, 2=+12dB

# Phase 2: Master section constants
BPM_MIN = 20
BPM_MAX = 300
BPM_DEFAULT = 120
COMP_RATIOS = 3       # 0=2:1, 1=4:1, 2=10:1
COMP_ATTACKS = 6      # 0-5: 0.1, 0.3, 1, 3, 10, 30ms
COMP_RELEASES = 5     # 0-4: 0.1, 0.3, 0.6, 1.2, Auto
COMP_SC_FREQS = 6     # 0-5: Off, 30, 60, 90, 120, 185Hz

# Phase 3: Modulation sources constants
NUM_MOD_SLOTS = 4
NUM_MOD_OUTPUTS = 4
MOD_WAVEFORMS = 5     # saw, tri, sqr, sin, s&h
MOD_PHASES = 8        # 0°, 45°, 90°, ... 315°
MOD_POLARITIES = 2    # 0=NORM, 1=INV

# Phase 4: Modulation routing constants
NUM_MOD_BUSES = 16    # 4 slots × 4 outputs
MOD_POLARITIES_ROUTING = 3  # 0=bipolar, 1=uni+, 2=uni-

# Phase 5: FX constants
HEAT_CIRCUITS = 4     # 0=CLEAN, 1=TAPE, 2=TUBE, 3=CRUNCH
FILTER_MODES = 3      # 0=LP, 1=BP, 2=HP
HARMONICS_OPTIONS = 8 # Free, 1, 2, 3, 4, 5, 8, 16
ROUTING_OPTIONS = 2   # 0=SER, 1=PAR


@dataclass
class SlotState:
    generator: Optional[str] = None
    frequency: float = 0.5
    cutoff: float = 0.5
    resonance: float = 0.0
    attack: float = 0.1
    decay: float = 0.3
    custom_0: float = 0.5
    custom_1: float = 0.5
    custom_2: float = 0.5
    custom_3: float = 0.5
    custom_4: float = 0.5
    filter_type: int = 0
    env_source: int = 0
    clock_rate: int = 4
    midi_channel: int = 1
    transpose: int = 2  # Index into TRANSPOSE_OPTIONS (0-4), default 2 = 0 semitones
    portamento: float = 0.0  # 0-1 normalized glide time
    
    def to_dict(self) -> dict:
        return {
            "generator": self.generator,
            "params": {
                "frequency": self.frequency,
                "cutoff": self.cutoff,
                "resonance": self.resonance,
                "attack": self.attack,
                "decay": self.decay,
                "custom_0": self.custom_0,
                "custom_1": self.custom_1,
                "custom_2": self.custom_2,
                "custom_3": self.custom_3,
                "custom_4": self.custom_4,
            },
            "filter_type": self.filter_type,
            "env_source": self.env_source,
            "clock_rate": self.clock_rate,
            "midi_channel": self.midi_channel,
            "transpose": self.transpose,
            "portamento": self.portamento,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SlotState":
        params = data.get("params", {})
        return cls(
            generator=data.get("generator"),
            frequency=params.get("frequency", 0.5),
            cutoff=params.get("cutoff", 0.5),
            resonance=params.get("resonance", 0.0),
            attack=params.get("attack", 0.1),
            decay=params.get("decay", 0.3),
            custom_0=params.get("custom_0", 0.5),
            custom_1=params.get("custom_1", 0.5),
            custom_2=params.get("custom_2", 0.5),
            custom_3=params.get("custom_3", 0.5),
            custom_4=params.get("custom_4", 0.5),
            filter_type=data.get("filter_type", 0),
            env_source=data.get("env_source", 0),
            clock_rate=data.get("clock_rate", 4),
            midi_channel=data.get("midi_channel", 1),
            transpose=data.get("transpose", 2),
            portamento=data.get("portamento", 0.0),
        )


@dataclass 
class ChannelState:
    """Channel strip state - Phase 1 expanded."""
    # Existing
    volume: float = 0.8
    pan: float = 0.5
    mute: bool = False
    solo: bool = False
    # Phase 1 additions
    eq_hi: int = 100    # 0-200, 100 = 0dB
    eq_mid: int = 100   # 0-200, 100 = 0dB
    eq_lo: int = 100    # 0-200, 100 = 0dB
    gain: int = 0       # Index: 0=0dB, 1=+6dB, 2=+12dB
    echo_send: int = 0  # 0-200
    verb_send: int = 0  # 0-200
    lo_cut: bool = False
    hi_cut: bool = False
    
    def to_dict(self) -> dict:
        return {
            "volume": self.volume,
            "pan": self.pan,
            "mute": self.mute,
            "solo": self.solo,
            "eq_hi": self.eq_hi,
            "eq_mid": self.eq_mid,
            "eq_lo": self.eq_lo,
            "gain": self.gain,
            "echo_send": self.echo_send,
            "verb_send": self.verb_send,
            "lo_cut": self.lo_cut,
            "hi_cut": self.hi_cut,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChannelState":
        return cls(
            volume=data.get("volume", 0.8),
            pan=data.get("pan", 0.5),
            mute=data.get("mute", False),
            solo=data.get("solo", False),
            eq_hi=data.get("eq_hi", 100),
            eq_mid=data.get("eq_mid", 100),
            eq_lo=data.get("eq_lo", 100),
            gain=data.get("gain", 0),
            echo_send=data.get("echo_send", 0),
            verb_send=data.get("verb_send", 0),
            lo_cut=data.get("lo_cut", False),
            hi_cut=data.get("hi_cut", False),
        )


@dataclass
class MasterState:
    """Master section state - Phase 2."""
    # Master volume (0-1000 slider, stored as 0-1 float)
    volume: float = 0.8
    
    # EQ (sliders 0-240, 120 = 0dB)
    eq_hi: int = 120
    eq_mid: int = 120
    eq_lo: int = 120
    eq_hi_kill: int = 0    # 0=off, 1=killed
    eq_mid_kill: int = 0
    eq_lo_kill: int = 0
    eq_locut: int = 0      # 0=off, 1=on
    eq_bypass: int = 0     # 0=on, 1=bypassed
    
    # Compressor
    comp_threshold: int = 100   # 0-400, 200=0dB
    comp_makeup: int = 0        # 0-200
    comp_ratio: int = 1         # index 0-2
    comp_attack: int = 4        # index 0-5
    comp_release: int = 4       # index 0-4
    comp_sc: int = 0            # index 0-5
    comp_bypass: int = 0        # 0=on, 1=bypassed
    
    # Limiter
    limiter_ceiling: int = 590  # 0-600, 590=-0.1dB
    limiter_bypass: int = 0     # 0=on, 1=bypassed
    
    def to_dict(self) -> dict:
        return {
            "volume": self.volume,
            "eq_hi": self.eq_hi,
            "eq_mid": self.eq_mid,
            "eq_lo": self.eq_lo,
            "eq_hi_kill": self.eq_hi_kill,
            "eq_mid_kill": self.eq_mid_kill,
            "eq_lo_kill": self.eq_lo_kill,
            "eq_locut": self.eq_locut,
            "eq_bypass": self.eq_bypass,
            "comp_threshold": self.comp_threshold,
            "comp_makeup": self.comp_makeup,
            "comp_ratio": self.comp_ratio,
            "comp_attack": self.comp_attack,
            "comp_release": self.comp_release,
            "comp_sc": self.comp_sc,
            "comp_bypass": self.comp_bypass,
            "limiter_ceiling": self.limiter_ceiling,
            "limiter_bypass": self.limiter_bypass,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MasterState":
        return cls(
            volume=data.get("volume", 0.8),
            eq_hi=data.get("eq_hi", 120),
            eq_mid=data.get("eq_mid", 120),
            eq_lo=data.get("eq_lo", 120),
            eq_hi_kill=data.get("eq_hi_kill", 0),
            eq_mid_kill=data.get("eq_mid_kill", 0),
            eq_lo_kill=data.get("eq_lo_kill", 0),
            eq_locut=data.get("eq_locut", 0),
            eq_bypass=data.get("eq_bypass", 0),
            comp_threshold=data.get("comp_threshold", 100),
            comp_makeup=data.get("comp_makeup", 0),
            comp_ratio=data.get("comp_ratio", 1),
            comp_attack=data.get("comp_attack", 4),
            comp_release=data.get("comp_release", 4),
            comp_sc=data.get("comp_sc", 0),
            comp_bypass=data.get("comp_bypass", 0),
            limiter_ceiling=data.get("limiter_ceiling", 590),
            limiter_bypass=data.get("limiter_bypass", 0),
        )


@dataclass
class MixerState:
    """Mixer state."""
    channels: list = field(default_factory=lambda: [ChannelState() for _ in range(NUM_SLOTS)])
    master_volume: float = 0.8
    
    def to_dict(self) -> dict:
        return {
            "channels": [ch.to_dict() for ch in self.channels],
            "master_volume": self.master_volume,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MixerState":
        channels = [
            ChannelState.from_dict(ch) 
            for ch in data.get("channels", [{}] * NUM_SLOTS)
        ]
        while len(channels) < NUM_SLOTS:
            channels.append(ChannelState())
        return cls(
            channels=channels[:NUM_SLOTS],
            master_volume=data.get("master_volume", 0.8),
        )


@dataclass
class ModSlotState:
    """Modulation source slot state - Phase 3."""
    generator_name: str = "Empty"  # "Empty", "LFO", "Sloth", etc.
    params: dict = field(default_factory=dict)  # key -> normalized 0-1 value
    output_wave: list = field(default_factory=lambda: [0, 0, 0, 0])  # 4 outputs
    output_phase: list = field(default_factory=lambda: [0, 3, 5, 6])  # Default phases for LFO
    output_polarity: list = field(default_factory=lambda: [0, 0, 0, 0])  # 0=NORM, 1=INV
    
    def to_dict(self) -> dict:
        return {
            "generator_name": self.generator_name,
            "params": dict(self.params),
            "output_wave": list(self.output_wave),
            "output_phase": list(self.output_phase),
            "output_polarity": list(self.output_polarity),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModSlotState":
        return cls(
            generator_name=data.get("generator_name", "Empty"),
            params=dict(data.get("params", {})),
            output_wave=list(data.get("output_wave", [0, 0, 0, 0])),
            output_phase=list(data.get("output_phase", [0, 3, 5, 6])),
            output_polarity=list(data.get("output_polarity", [0, 0, 0, 0])),
        )


@dataclass
class ModSourcesState:
    """All modulation sources - Phase 3."""
    slots: list = field(default_factory=lambda: [ModSlotState() for _ in range(NUM_MOD_SLOTS)])
    
    def to_dict(self) -> dict:
        return {
            "slots": [slot.to_dict() for slot in self.slots]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModSourcesState":
        slots_data = data.get("slots", [{}] * NUM_MOD_SLOTS)
        slots = [ModSlotState.from_dict(s) for s in slots_data]
        while len(slots) < NUM_MOD_SLOTS:
            slots.append(ModSlotState())
        return cls(slots=slots[:NUM_MOD_SLOTS])


# Phase 5: FX State dataclasses

@dataclass
class HeatState:
    """Heat saturation state."""
    bypass: bool = True  # True = bypassed, False = active
    circuit: int = 0     # 0=CLEAN, 1=TAPE, 2=TUBE, 3=CRUNCH
    drive: int = 0       # 0-100
    mix: int = 100       # 0-100
    
    def to_dict(self) -> dict:
        return {
            "bypass": self.bypass,
            "circuit": self.circuit,
            "drive": self.drive,
            "mix": self.mix,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "HeatState":
        return cls(
            bypass=data.get("bypass", True),
            circuit=data.get("circuit", 0),
            drive=data.get("drive", 0),
            mix=data.get("mix", 100),
        )


@dataclass
class EchoState:
    """Tape echo state."""
    time: int = 40       # 0-100
    feedback: int = 30   # 0-100
    tone: int = 70       # 0-100
    wow: int = 10        # 0-100
    spring: int = 0      # 0-100
    verb_send: int = 0   # 0-100
    return_level: int = 50  # 0-100
    
    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "feedback": self.feedback,
            "tone": self.tone,
            "wow": self.wow,
            "spring": self.spring,
            "verb_send": self.verb_send,
            "return_level": self.return_level,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EchoState":
        return cls(
            time=data.get("time", 40),
            feedback=data.get("feedback", 30),
            tone=data.get("tone", 70),
            wow=data.get("wow", 10),
            spring=data.get("spring", 0),
            verb_send=data.get("verb_send", 0),
            return_level=data.get("return_level", 50),
        )


@dataclass
class ReverbState:
    """Reverb state."""
    size: int = 50       # 0-100
    decay: int = 50      # 0-100
    tone: int = 70       # 0-100
    return_level: int = 30  # 0-100
    
    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "decay": self.decay,
            "tone": self.tone,
            "return_level": self.return_level,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ReverbState":
        return cls(
            size=data.get("size", 50),
            decay=data.get("decay", 50),
            tone=data.get("tone", 70),
            return_level=data.get("return_level", 30),
        )


@dataclass
class DualFilterState:
    """Dual filter state."""
    bypass: bool = True  # True = bypassed, False = active
    drive: int = 0       # 0-100
    freq1: int = 50      # 0-100
    reso1: int = 0       # 0-100
    mode1: int = 1       # 0=LP, 1=BP, 2=HP
    freq2: int = 35      # 0-100
    reso2: int = 0       # 0-100
    mode2: int = 1       # 0=LP, 1=BP, 2=HP
    harmonics: int = 0   # 0-7 (Free, 1, 2, 3, 4, 5, 8, 16)
    routing: int = 0     # 0=SER, 1=PAR
    mix: int = 100       # 0-100
    
    def to_dict(self) -> dict:
        return {
            "bypass": self.bypass,
            "drive": self.drive,
            "freq1": self.freq1,
            "reso1": self.reso1,
            "mode1": self.mode1,
            "freq2": self.freq2,
            "reso2": self.reso2,
            "mode2": self.mode2,
            "harmonics": self.harmonics,
            "routing": self.routing,
            "mix": self.mix,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DualFilterState":
        return cls(
            bypass=data.get("bypass", True),
            drive=data.get("drive", 0),
            freq1=data.get("freq1", 50),
            reso1=data.get("reso1", 0),
            mode1=data.get("mode1", 1),
            freq2=data.get("freq2", 35),
            reso2=data.get("reso2", 0),
            mode2=data.get("mode2", 1),
            harmonics=data.get("harmonics", 0),
            routing=data.get("routing", 0),
            mix=data.get("mix", 100),
        )


@dataclass
class FXState:
    """Master FX state - Phase 5."""
    heat: HeatState = field(default_factory=HeatState)
    echo: EchoState = field(default_factory=EchoState)
    reverb: ReverbState = field(default_factory=ReverbState)
    dual_filter: DualFilterState = field(default_factory=DualFilterState)
    
    def to_dict(self) -> dict:
        return {
            "heat": self.heat.to_dict(),
            "echo": self.echo.to_dict(),
            "reverb": self.reverb.to_dict(),
            "dual_filter": self.dual_filter.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FXState":
        if not isinstance(data, dict):
            data = {}
        return cls(
            heat=HeatState.from_dict(data.get("heat", {})),
            echo=EchoState.from_dict(data.get("echo", {})),
            reverb=ReverbState.from_dict(data.get("reverb", {})),
            dual_filter=DualFilterState.from_dict(data.get("dual_filter", {})),
        )


@dataclass
class PresetState:
    version: int = PRESET_VERSION
    mapping_version: int = MAPPING_VERSION
    name: str = "Untitled"
    created: str = ""
    pack: Optional[str] = None  # None = Core, string = pack_id
    slots: list = field(default_factory=lambda: [SlotState() for _ in range(NUM_SLOTS)])
    mixer: MixerState = field(default_factory=MixerState)
    # Phase 2 additions
    bpm: int = BPM_DEFAULT
    master: MasterState = field(default_factory=MasterState)
    # Phase 3 additions
    mod_sources: ModSourcesState = field(default_factory=ModSourcesState)
    # Phase 4 additions
    mod_routing: dict = field(default_factory=lambda: {"connections": []})
    # Phase 5 additions
    fx: FXState = field(default_factory=FXState)
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "mapping_version": self.mapping_version,
            "name": self.name,
            "created": self.created,
            "pack": self.pack,
            "slots": [slot.to_dict() for slot in self.slots],
            "mixer": self.mixer.to_dict(),
            "bpm": self.bpm,
            "master": self.master.to_dict(),
            "mod_sources": self.mod_sources.to_dict(),
            "mod_routing": self.mod_routing,
            "fx": self.fx.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PresetState":
        slots = [
            SlotState.from_dict(s) 
            for s in data.get("slots", [{}] * NUM_SLOTS)
        ]
        # Pad to NUM_SLOTS if fewer slots saved
        while len(slots) < NUM_SLOTS:
            slots.append(SlotState())
        return cls(
            version=data.get("version", PRESET_VERSION),
            mapping_version=data.get("mapping_version", MAPPING_VERSION),
            name=data.get("name", "Untitled"),
            created=data.get("created", ""),
            pack=data.get("pack"),  # None if not present (backward compat)
            slots=slots[:NUM_SLOTS],
            mixer=MixerState.from_dict(data.get("mixer", {})),
            bpm=data.get("bpm", BPM_DEFAULT),
            master=MasterState.from_dict(data.get("master", {})),
            mod_sources=ModSourcesState.from_dict(data.get("mod_sources", {})),
            mod_routing=data.get("mod_routing", {"connections": []}),
            fx=FXState.from_dict(data.get("fx", {})),
        )
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> "PresetState":
        data = json.loads(json_str)
        return cls.from_dict(data)


class PresetValidationError(Exception):
    """Raised when preset validation fails in strict mode."""
    pass


def validate_preset(data: dict, strict: bool = False) -> tuple:
    """
    Validate preset data.
    
    Args:
        data: Preset dictionary
        strict: If True, raise PresetValidationError on any issue
        
    Returns:
        (is_valid, errors_and_warnings)
    """
    errors = []
    warnings = []
    
    # Version check
    version = data.get("version", 1)
    if version > PRESET_VERSION:
        warnings.append(f"Preset version {version} is newer than supported {PRESET_VERSION}")
    
    # Slots validation
    slots = data.get("slots", [])
    if len(slots) != NUM_SLOTS:
        if strict:
            errors.append(f"slots must have exactly {NUM_SLOTS} items, got {len(slots)}")
        else:
            warnings.append(f"slots has {len(slots)} items, expected {NUM_SLOTS}")
    
    for i, slot in enumerate(slots[:NUM_SLOTS]):
        slot_errors, slot_warnings = _validate_slot(slot, f"slots[{i}]", strict)
        errors.extend(slot_errors)
        warnings.extend(slot_warnings)
    
    # Mixer validation
    mixer = data.get("mixer", {})
    mixer_errors, mixer_warnings = _validate_mixer(mixer, strict)
    errors.extend(mixer_errors)
    warnings.extend(mixer_warnings)
    
    # BPM validation
    bpm = data.get("bpm", BPM_DEFAULT)
    bpm, warning = _coerce_int(bpm, "bpm")
    if warning:
        warnings.append(warning)
    if bpm is not None and not (BPM_MIN <= bpm <= BPM_MAX):
        errors.append(f"bpm must be {BPM_MIN}-{BPM_MAX}, got {bpm}")
    
    # Master validation
    master = data.get("master", {})
    master_errors, master_warnings = _validate_master(master, strict)
    errors.extend(master_errors)
    warnings.extend(master_warnings)
    
    # Mod sources validation
    mod_sources = data.get("mod_sources", {})
    mod_sources_errors, mod_sources_warnings = _validate_mod_sources(mod_sources, strict)
    errors.extend(mod_sources_errors)
    warnings.extend(mod_sources_warnings)
    
    # Mod routing validation
    mod_routing = data.get("mod_routing", {})
    mod_routing_errors, mod_routing_warnings = _validate_mod_routing(mod_routing, strict)
    errors.extend(mod_routing_errors)
    warnings.extend(mod_routing_warnings)
    
    # FX validation
    fx = data.get("fx", {})
    fx_errors, fx_warnings = _validate_fx(fx, strict)
    errors.extend(fx_errors)
    warnings.extend(fx_warnings)
    
    is_valid = len(errors) == 0
    
    if strict and not is_valid:
        raise PresetValidationError(f"Invalid preset: {'; '.join(errors)}")
    
    return is_valid, errors + warnings


def _validate_slot(slot: dict, prefix: str, strict: bool = False) -> tuple:
    """Validate a single slot."""
    errors = []
    warnings = []
    
    if not isinstance(slot, dict):
        errors.append(f"{prefix} must be dict")
        return errors, warnings
    
    # Params validation
    params = slot.get("params", {})
    if not isinstance(params, dict):
        errors.append(f"{prefix}.params must be dict")
    else:
        for key in ["frequency", "cutoff", "resonance", "attack", "decay",
                    "custom_0", "custom_1", "custom_2", "custom_3", "custom_4"]:
            val = params.get(key)
            if val is not None:
                val, warning = _coerce_float(val, f"{prefix}.params.{key}")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0.0 <= val <= 1.0):
                    errors.append(f"{prefix}.params.{key} must be 0-1, got {val}")
    
    # Filter type
    ft = slot.get("filter_type", 0)
    ft, warning = _coerce_int(ft, f"{prefix}.filter_type")
    if warning:
        warnings.append(warning)
    if ft is not None and not (0 <= ft < FILTER_TYPES):
        errors.append(f"{prefix}.filter_type must be 0-{FILTER_TYPES-1}, got {ft}")
    
    # Env source
    es = slot.get("env_source", 0)
    es, warning = _coerce_int(es, f"{prefix}.env_source")
    if warning:
        warnings.append(warning)
    if es is not None and not (0 <= es < ENV_SOURCES):
        errors.append(f"{prefix}.env_source must be 0-{ENV_SOURCES-1}, got {es}")
    
    # Clock rate
    cr = slot.get("clock_rate", 4)
    cr, warning = _coerce_int(cr, f"{prefix}.clock_rate")
    if warning:
        warnings.append(warning)
    if cr is not None and not (0 <= cr < CLOCK_RATES):
        errors.append(f"{prefix}.clock_rate must be 0-{CLOCK_RATES-1}, got {cr}")
    
    # MIDI channel
    mc = slot.get("midi_channel", 1)
    mc, warning = _coerce_int(mc, f"{prefix}.midi_channel")
    if warning:
        warnings.append(warning)
    if mc is not None and not (0 <= mc <= MIDI_CHANNELS):
        errors.append(f"{prefix}.midi_channel must be 0-{MIDI_CHANNELS}, got {mc}")
    
    # Transpose
    tr = slot.get("transpose", 2)
    tr, warning = _coerce_int(tr, f"{prefix}.transpose")
    if warning:
        warnings.append(warning)
    if tr is not None and not (0 <= tr <= 4):
        errors.append(f"{prefix}.transpose must be 0-4, got {tr}")
    
    # Portamento
    port = slot.get("portamento", 0.0)
    port, warning = _coerce_float(port, f"{prefix}.portamento")
    if warning:
        warnings.append(warning)
    if port is not None and not (0.0 <= port <= 1.0):
        errors.append(f"{prefix}.portamento must be 0-1, got {port}")
    
    return errors, warnings


def _validate_mixer(mixer: dict, strict: bool = False) -> tuple:
    """Validate mixer state."""
    errors = []
    warnings = []
    
    if not isinstance(mixer, dict):
        errors.append("mixer must be dict")
        return errors, warnings
    
    channels = mixer.get("channels", [])
    if len(channels) != NUM_SLOTS:
        if strict:
            errors.append(f"mixer.channels must have exactly {NUM_SLOTS} items, got {len(channels)}")
        else:
            warnings.append(f"mixer.channels has {len(channels)} items, expected {NUM_SLOTS}")
    
    for i, ch in enumerate(channels[:NUM_SLOTS]):
        ch_errors, ch_warnings = _validate_channel(ch, f"mixer.channels[{i}]", strict)
        errors.extend(ch_errors)
        warnings.extend(ch_warnings)
    
    # Master volume
    mv = mixer.get("master_volume", 0.8)
    mv, warning = _coerce_float(mv, "mixer.master_volume")
    if warning:
        warnings.append(warning)
    if mv is not None and not (0.0 <= mv <= 1.0):
        errors.append(f"mixer.master_volume must be 0-1, got {mv}")
    
    return errors, warnings


def _validate_channel(channel: dict, prefix: str, strict: bool = False) -> tuple:
    """Validate a single channel."""
    errors = []
    warnings = []
    
    if not isinstance(channel, dict):
        errors.append(f"{prefix} must be dict")
        return errors, warnings
    
    # Volume and pan
    for key in ["volume", "pan"]:
        val = channel.get(key)
        if val is not None:
            val, warning = _coerce_float(val, f"{prefix}.{key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0.0 <= val <= 1.0):
                errors.append(f"{prefix}.{key} must be 0-1, got {val}")
    
    # Booleans
    for key in ["mute", "solo", "lo_cut", "hi_cut"]:
        val = channel.get(key)
        if val is not None and not isinstance(val, bool):
            errors.append(f"{prefix}.{key} must be bool, got {type(val).__name__}")
    
    # EQ values (0-200)
    for key in ["eq_hi", "eq_mid", "eq_lo", "echo_send", "verb_send"]:
        val = channel.get(key)
        if val is not None:
            val, warning = _coerce_int(val, f"{prefix}.{key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0 <= val <= 200):
                errors.append(f"{prefix}.{key} must be 0-200, got {val}")
    
    # Gain (0-2)
    gain = channel.get("gain", 0)
    gain, warning = _coerce_int(gain, f"{prefix}.gain")
    if warning:
        warnings.append(warning)
    if gain is not None and not (0 <= gain < GAIN_STAGES):
        errors.append(f"{prefix}.gain must be 0-{GAIN_STAGES-1}, got {gain}")
    
    return errors, warnings


def _validate_master(master: dict, strict: bool = False) -> tuple:
    """Validate master section state."""
    errors = []
    warnings = []
    
    if not isinstance(master, dict):
        errors.append("master must be dict")
        return errors, warnings
    
    # Volume (0-1)
    vol = master.get("volume", 0.8)
    vol, warning = _coerce_float(vol, "master.volume")
    if warning:
        warnings.append(warning)
    if vol is not None and not (0.0 <= vol <= 1.0):
        errors.append(f"master.volume must be 0-1, got {vol}")
    
    # EQ sliders (0-240)
    for key in ["eq_hi", "eq_mid", "eq_lo"]:
        val = master.get(key)
        if val is not None:
            val, warning = _coerce_int(val, f"master.{key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0 <= val <= 240):
                errors.append(f"master.{key} must be 0-240, got {val}")
    
    # EQ buttons (0-1)
    for key in ["eq_hi_kill", "eq_mid_kill", "eq_lo_kill", "eq_locut", "eq_bypass"]:
        val = master.get(key)
        if val is not None:
            val, warning = _coerce_int(val, f"master.{key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0 <= val <= 1):
                errors.append(f"master.{key} must be 0-1, got {val}")
    
    # Compressor threshold (0-400)
    ct = master.get("comp_threshold")
    if ct is not None:
        ct, warning = _coerce_int(ct, "master.comp_threshold")
        if warning:
            warnings.append(warning)
        if ct is not None and not (0 <= ct <= 400):
            errors.append(f"master.comp_threshold must be 0-400, got {ct}")
    
    # Compressor makeup (0-200)
    cm = master.get("comp_makeup")
    if cm is not None:
        cm, warning = _coerce_int(cm, "master.comp_makeup")
        if warning:
            warnings.append(warning)
        if cm is not None and not (0 <= cm <= 200):
            errors.append(f"master.comp_makeup must be 0-200, got {cm}")
    
    # Compressor indices
    for key, max_val in [("comp_ratio", COMP_RATIOS), ("comp_attack", COMP_ATTACKS),
                          ("comp_release", COMP_RELEASES), ("comp_sc", COMP_SC_FREQS)]:
        val = master.get(key)
        if val is not None:
            val, warning = _coerce_int(val, f"master.{key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0 <= val < max_val):
                errors.append(f"master.{key} must be 0-{max_val-1}, got {val}")
    
    # Compressor bypass
    cb = master.get("comp_bypass")
    if cb is not None:
        cb, warning = _coerce_int(cb, "master.comp_bypass")
        if warning:
            warnings.append(warning)
        if cb is not None and not (0 <= cb <= 1):
            errors.append(f"master.comp_bypass must be 0-1, got {cb}")
    
    # Limiter ceiling (0-600)
    lc = master.get("limiter_ceiling")
    if lc is not None:
        lc, warning = _coerce_int(lc, "master.limiter_ceiling")
        if warning:
            warnings.append(warning)
        if lc is not None and not (0 <= lc <= 600):
            errors.append(f"master.limiter_ceiling must be 0-600, got {lc}")
    
    # Limiter bypass
    lb = master.get("limiter_bypass")
    if lb is not None:
        lb, warning = _coerce_int(lb, "master.limiter_bypass")
        if warning:
            warnings.append(warning)
        if lb is not None and not (0 <= lb <= 1):
            errors.append(f"master.limiter_bypass must be 0-1, got {lb}")
    
    return errors, warnings


def _validate_mod_sources(mod_sources: dict, strict: bool = False) -> tuple:
    """Validate modulation sources state (Phase 3)."""
    errors = []
    warnings = []
    
    if not isinstance(mod_sources, dict):
        errors.append("mod_sources must be dict")
        return errors, warnings
    
    slots = mod_sources.get("slots", [])
    if len(slots) != NUM_MOD_SLOTS:
        if strict:
            errors.append(f"mod_sources.slots must have exactly {NUM_MOD_SLOTS} items, got {len(slots)}")
        else:
            warnings.append(f"mod_sources.slots has {len(slots)} items, expected {NUM_MOD_SLOTS}")
    
    for i, slot in enumerate(slots[:NUM_MOD_SLOTS]):
        if not isinstance(slot, dict):
            errors.append(f"mod_sources.slots[{i}] must be dict")
            continue
        
        prefix = f"mod_sources.slots[{i}]"
        
        # generator_name must be string
        gen_name = slot.get("generator_name", "Empty")
        if not isinstance(gen_name, str):
            errors.append(f"{prefix}.generator_name must be string")
        
        # params must be dict
        params = slot.get("params", {})
        if not isinstance(params, dict):
            errors.append(f"{prefix}.params must be dict")
        else:
            # Validate param values are 0-1
            for key, val in params.items():
                val, warning = _coerce_float(val, f"{prefix}.params.{key}")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0.0 <= val <= 1.0):
                    errors.append(f"{prefix}.params.{key} must be 0-1, got {val}")
        
        # output_wave must be list of 4 ints
        output_wave = slot.get("output_wave", [0, 0, 0, 0])
        if not isinstance(output_wave, list):
            errors.append(f"{prefix}.output_wave must be list")
        elif len(output_wave) != NUM_MOD_OUTPUTS:
            if strict:
                errors.append(f"{prefix}.output_wave must have {NUM_MOD_OUTPUTS} items, got {len(output_wave)}")
            else:
                warnings.append(f"{prefix}.output_wave has {len(output_wave)} items, expected {NUM_MOD_OUTPUTS}")
        else:
            for j, val in enumerate(output_wave):
                val, warning = _coerce_int(val, f"{prefix}.output_wave[{j}]")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0 <= val < MOD_WAVEFORMS):
                    errors.append(f"{prefix}.output_wave[{j}] must be 0-{MOD_WAVEFORMS-1}, got {val}")
        
        # output_phase must be list of 4 ints
        output_phase = slot.get("output_phase", [0, 3, 5, 6])
        if not isinstance(output_phase, list):
            errors.append(f"{prefix}.output_phase must be list")
        elif len(output_phase) != NUM_MOD_OUTPUTS:
            if strict:
                errors.append(f"{prefix}.output_phase must have {NUM_MOD_OUTPUTS} items, got {len(output_phase)}")
            else:
                warnings.append(f"{prefix}.output_phase has {len(output_phase)} items, expected {NUM_MOD_OUTPUTS}")
        else:
            for j, val in enumerate(output_phase):
                val, warning = _coerce_int(val, f"{prefix}.output_phase[{j}]")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0 <= val < MOD_PHASES):
                    errors.append(f"{prefix}.output_phase[{j}] must be 0-{MOD_PHASES-1}, got {val}")
        
        # output_polarity must be list of 4 ints
        output_polarity = slot.get("output_polarity", [0, 0, 0, 0])
        if not isinstance(output_polarity, list):
            errors.append(f"{prefix}.output_polarity must be list")
        elif len(output_polarity) != NUM_MOD_OUTPUTS:
            if strict:
                errors.append(f"{prefix}.output_polarity must have {NUM_MOD_OUTPUTS} items, got {len(output_polarity)}")
            else:
                warnings.append(f"{prefix}.output_polarity has {len(output_polarity)} items, expected {NUM_MOD_OUTPUTS}")
        else:
            for j, val in enumerate(output_polarity):
                val, warning = _coerce_int(val, f"{prefix}.output_polarity[{j}]")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0 <= val < MOD_POLARITIES):
                    errors.append(f"{prefix}.output_polarity[{j}] must be 0-{MOD_POLARITIES-1}, got {val}")
    
    return errors, warnings


def _validate_mod_routing(mod_routing: dict, strict: bool = False) -> tuple:
    """Validate modulation routing state (Phase 4)."""
    errors = []
    warnings = []
    
    connections = mod_routing.get("connections", [])
    if not isinstance(connections, list):
        errors.append("mod_routing.connections must be a list")
        return errors, warnings
    
    for i, conn in enumerate(connections):
        if not isinstance(conn, dict):
            errors.append(f"mod_routing.connections[{i}] must be dict")
            continue
        
        prefix = f"mod_routing.connections[{i}]"
        
        # source_bus: 0-15
        source_bus = conn.get("source_bus")
        if source_bus is None:
            errors.append(f"{prefix}.source_bus is required")
        else:
            source_bus, warning = _coerce_int(source_bus, f"{prefix}.source_bus")
            if warning:
                warnings.append(warning)
            if source_bus is not None and not (0 <= source_bus < NUM_MOD_BUSES):
                errors.append(f"{prefix}.source_bus must be 0-{NUM_MOD_BUSES-1}, got {source_bus}")
        
        # target_slot: 1-8 (1-indexed)
        target_slot = conn.get("target_slot")
        if target_slot is None:
            errors.append(f"{prefix}.target_slot is required")
        else:
            target_slot, warning = _coerce_int(target_slot, f"{prefix}.target_slot")
            if warning:
                warnings.append(warning)
            if target_slot is not None and not (1 <= target_slot <= NUM_SLOTS):
                errors.append(f"{prefix}.target_slot must be 1-{NUM_SLOTS}, got {target_slot}")
        
        # target_param: must be string
        target_param = conn.get("target_param")
        if target_param is None:
            errors.append(f"{prefix}.target_param is required")
        elif not isinstance(target_param, str):
            errors.append(f"{prefix}.target_param must be string")
        
        # depth: 0-1 (optional, defaults to 1.0)
        depth = conn.get("depth", 1.0)
        depth, warning = _coerce_float(depth, f"{prefix}.depth")
        if warning:
            warnings.append(warning)
        if depth is not None and not (0.0 <= depth <= 1.0):
            errors.append(f"{prefix}.depth must be 0-1, got {depth}")
        
        # amount: 0-1 (optional)
        amount = conn.get("amount", 0.5)
        amount, warning = _coerce_float(amount, f"{prefix}.amount")
        if warning:
            warnings.append(warning)
        if amount is not None and not (0.0 <= amount <= 1.0):
            errors.append(f"{prefix}.amount must be 0-1, got {amount}")
        
        # offset: -1 to +1 (optional)
        offset = conn.get("offset", 0.0)
        offset, warning = _coerce_float(offset, f"{prefix}.offset")
        if warning:
            warnings.append(warning)
        if offset is not None and not (-1.0 <= offset <= 1.0):
            errors.append(f"{prefix}.offset must be -1 to +1, got {offset}")
        
        # polarity: 0-2 (optional)
        polarity = conn.get("polarity", 0)
        polarity, warning = _coerce_int(polarity, f"{prefix}.polarity")
        if warning:
            warnings.append(warning)
        if polarity is not None and not (0 <= polarity < MOD_POLARITIES_ROUTING):
            errors.append(f"{prefix}.polarity must be 0-{MOD_POLARITIES_ROUTING-1}, got {polarity}")
        
        # invert: bool (optional)
        invert = conn.get("invert", False)
        if not isinstance(invert, bool):
            errors.append(f"{prefix}.invert must be bool, got {type(invert).__name__}")
    
    return errors, warnings


def _validate_fx(fx: dict, strict: bool = False) -> tuple:
    """Validate FX state (Phase 5)."""
    errors = []
    warnings = []

    # FX section is optional for backward compatibility, BUT if present it must be a dict.
    if fx is None:
        return errors, warnings
    if not isinstance(fx, dict):
        msg = f"fx must be dict, got {type(fx).__name__}"
        (errors if strict else warnings).append(msg)
        return errors, warnings
    
    # Heat validation
    heat = fx.get("heat", {})
    if isinstance(heat, dict):
        # bypass
        bypass = heat.get("bypass")
        if bypass is not None and not isinstance(bypass, bool):
            errors.append(f"fx.heat.bypass must be bool")
        
        # circuit (0-3)
        circuit = heat.get("circuit")
        if circuit is not None:
            circuit, warning = _coerce_int(circuit, "fx.heat.circuit")
            if warning:
                warnings.append(warning)
            if circuit is not None and not (0 <= circuit < HEAT_CIRCUITS):
                errors.append(f"fx.heat.circuit must be 0-{HEAT_CIRCUITS-1}, got {circuit}")
        
        # drive, mix (0-100)
        for key in ["drive", "mix"]:
            val = heat.get(key)
            if val is not None:
                val, warning = _coerce_int(val, f"fx.heat.{key}")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0 <= val <= 100):
                    errors.append(f"fx.heat.{key} must be 0-100, got {val}")
    
    # Echo validation
    echo = fx.get("echo", {})
    if isinstance(echo, dict):
        for key in ["time", "feedback", "tone", "wow", "spring", "verb_send", "return_level"]:
            val = echo.get(key)
            if val is not None:
                val, warning = _coerce_int(val, f"fx.echo.{key}")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0 <= val <= 100):
                    errors.append(f"fx.echo.{key} must be 0-100, got {val}")
    
    # Reverb validation
    reverb = fx.get("reverb", {})
    if isinstance(reverb, dict):
        for key in ["size", "decay", "tone", "return_level"]:
            val = reverb.get(key)
            if val is not None:
                val, warning = _coerce_int(val, f"fx.reverb.{key}")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0 <= val <= 100):
                    errors.append(f"fx.reverb.{key} must be 0-100, got {val}")
    
    # Dual filter validation
    df = fx.get("dual_filter", {})
    if isinstance(df, dict):
        # bypass
        bypass = df.get("bypass")
        if bypass is not None and not isinstance(bypass, bool):
            errors.append(f"fx.dual_filter.bypass must be bool")
        
        # knobs (0-100)
        for key in ["drive", "freq1", "reso1", "freq2", "reso2", "mix"]:
            val = df.get(key)
            if val is not None:
                val, warning = _coerce_int(val, f"fx.dual_filter.{key}")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0 <= val <= 100):
                    errors.append(f"fx.dual_filter.{key} must be 0-100, got {val}")
        
        # mode1, mode2 (0-2)
        for key in ["mode1", "mode2"]:
            val = df.get(key)
            if val is not None:
                val, warning = _coerce_int(val, f"fx.dual_filter.{key}")
                if warning:
                    warnings.append(warning)
                if val is not None and not (0 <= val < FILTER_MODES):
                    errors.append(f"fx.dual_filter.{key} must be 0-{FILTER_MODES-1}, got {val}")
        
        # harmonics (0-7)
        harmonics = df.get("harmonics")
        if harmonics is not None:
            harmonics, warning = _coerce_int(harmonics, "fx.dual_filter.harmonics")
            if warning:
                warnings.append(warning)
            if harmonics is not None and not (0 <= harmonics < HARMONICS_OPTIONS):
                errors.append(f"fx.dual_filter.harmonics must be 0-{HARMONICS_OPTIONS-1}, got {harmonics}")
        
        # routing (0-1)
        routing = df.get("routing")
        if routing is not None:
            routing, warning = _coerce_int(routing, "fx.dual_filter.routing")
            if warning:
                warnings.append(warning)
            if routing is not None and not (0 <= routing < ROUTING_OPTIONS):
                errors.append(f"fx.dual_filter.routing must be 0-{ROUTING_OPTIONS-1}, got {routing}")
    
    return errors, warnings


def _coerce_float(val, field_name: str) -> tuple:
    """
    Coerce value to float, accepting integral floats with warning.
    Returns (coerced_value, warning_message).
    """
    if val is None:
        return None, None
    if isinstance(val, float):
        if val != val:  # NaN check
            return None, f"{field_name}: NaN rejected"
        if val == float('inf') or val == float('-inf'):
            return None, f"{field_name}: Inf rejected"
        return val, None
    if isinstance(val, int) and not isinstance(val, bool):
        return float(val), None
    return None, f"{field_name}: invalid type {type(val).__name__}"


def _coerce_int(val, field_name: str) -> tuple:
    """
    Coerce value to int, accepting integral floats with warning.
    Returns (coerced_value, warning_message).
    """
    if val is None:
        return None, None
    if isinstance(val, int) and not isinstance(val, bool):
        return val, None
    if isinstance(val, float):
        if val != val:  # NaN check
            return None, f"{field_name}: NaN rejected"
        if val == float('inf') or val == float('-inf'):
            return None, f"{field_name}: Inf rejected"
        if val.is_integer():
            return int(val), f"{field_name}: coerced float {val} to int"
        return None, f"{field_name}: non-integral float {val}"
    return None, f"{field_name}: invalid type {type(val).__name__}"
