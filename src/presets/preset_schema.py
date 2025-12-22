"""
Preset schema definition and validation.
v2 - Phase 1: Channel strip expansion (EQ, gain, sends, cuts)
   - Phase 2: BPM + Master section (EQ, compressor, limiter)
   - Phase 3: Modulation sources (4 slots × 4 outputs)
   - Phase 4: Modulation routing (connections)
"""

from dataclasses import dataclass, field
from typing import Optional
import json

PRESET_VERSION = 2
MAPPING_VERSION = 1  # For future UI→value curve changes

# Valid ranges
FILTER_TYPES = 3      # 0=LP, 1=HP, 2=BP
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
class ModSlotState:
    """Modulator slot state - Phase 3."""
    generator_name: str = "Empty"  # "Empty", "LFO", "Sloth", etc.
    params: dict = field(default_factory=dict)  # key -> normalized 0-1 value
    output_wave: list = field(default_factory=lambda: [0, 0, 0, 0])  # 4 outputs
    output_phase: list = field(default_factory=lambda: [0, 3, 5, 6])  # Default phases for LFO
    output_polarity: list = field(default_factory=lambda: [0, 0, 0, 0])  # 0=NORM, 1=INV
    
    def to_dict(self) -> dict:
        return {
            "generator_name": self.generator_name,
            "params": dict(self.params),  # Copy
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
    """All modulator slots state - Phase 3."""
    slots: list = field(default_factory=lambda: [ModSlotState() for _ in range(NUM_MOD_SLOTS)])
    
    def to_dict(self) -> dict:
        return {
            "slots": [slot.to_dict() for slot in self.slots],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModSourcesState":
        slots_data = data.get("slots", [{}] * NUM_MOD_SLOTS)
        slots = [ModSlotState.from_dict(s) for s in slots_data]
        # Pad to NUM_MOD_SLOTS if fewer
        while len(slots) < NUM_MOD_SLOTS:
            slots.append(ModSlotState())
        return cls(slots=slots[:NUM_MOD_SLOTS])


@dataclass
class MixerState:
    channels: list = field(default_factory=lambda: [ChannelState() for _ in range(NUM_SLOTS)])
    master_volume: float = 0.8  # Kept for backward compat, but master.volume is canonical
    
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
        # Pad to NUM_SLOTS if fewer channels saved
        while len(channels) < NUM_SLOTS:
            channels.append(ChannelState())
        return cls(
            channels=channels[:NUM_SLOTS],
            master_volume=data.get("master_volume", 0.8),
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
    Validate preset data structure.
    
    Args:
        data: Preset data dict
        strict: If True, raise PresetValidationError on any issue.
                If False, return errors/warnings list (best-effort mode).
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    warnings = []
    
    # Check version
    version = data.get("version")
    if version is None:
        errors.append("Missing version field")
    elif version > PRESET_VERSION:
        errors.append(f"Preset version {version} is newer than supported {PRESET_VERSION}")
    
    # Check slots
    slots = data.get("slots", [])
    if not isinstance(slots, list):
        errors.append("slots must be a list")
    elif len(slots) != NUM_SLOTS:
        if strict:
            errors.append(f"slots must have exactly {NUM_SLOTS} items, got {len(slots)}")
        else:
            warnings.append(f"slots has {len(slots)} items, expected {NUM_SLOTS}")
    
    if isinstance(slots, list):
        for i, slot in enumerate(slots[:NUM_SLOTS]):
            slot_errors, slot_warnings = _validate_slot(slot, i, strict)
            errors.extend(slot_errors)
            warnings.extend(slot_warnings)
    
    # Check mixer
    mixer = data.get("mixer", {})
    if not isinstance(mixer, dict):
        errors.append("mixer must be a dict")
    else:
        mixer_errors, mixer_warnings = _validate_mixer(mixer, strict)
        errors.extend(mixer_errors)
        warnings.extend(mixer_warnings)
    
    # Check BPM (Phase 2)
    bpm = data.get("bpm", BPM_DEFAULT)
    bpm, warning = _coerce_int(bpm, "bpm")
    if warning:
        warnings.append(warning)
    if bpm is not None and not (BPM_MIN <= bpm <= BPM_MAX):
        errors.append(f"bpm must be {BPM_MIN}-{BPM_MAX}, got {bpm}")
    
    # Check master (Phase 2)
    master = data.get("master", {})
    if master and not isinstance(master, dict):
        errors.append("master must be a dict")
    elif master:
        master_errors, master_warnings = _validate_master(master, strict)
        errors.extend(master_errors)
        warnings.extend(master_warnings)
    
    # Check mod_sources (Phase 3)
    mod_sources = data.get("mod_sources", {})
    if mod_sources and not isinstance(mod_sources, dict):
        errors.append("mod_sources must be a dict")
    elif mod_sources:
        mod_errors, mod_warnings = _validate_mod_sources(mod_sources, strict)
        errors.extend(mod_errors)
        warnings.extend(mod_warnings)
    
    # Check mod_routing (Phase 4)
    mod_routing = data.get("mod_routing", {})
    if mod_routing and not isinstance(mod_routing, dict):
        errors.append("mod_routing must be a dict")
    elif mod_routing:
        routing_errors, routing_warnings = _validate_mod_routing(mod_routing, strict)
        errors.extend(routing_errors)
        warnings.extend(routing_warnings)
    
    if strict and (errors or warnings):
        raise PresetValidationError(errors + warnings)
    
    return len(errors) == 0, errors + warnings


def _validate_slot(slot: dict, index: int, strict: bool = False) -> tuple:
    """Validate a single slot."""
    errors = []
    warnings = []
    prefix = f"slots[{index}]"
    
    # Generator can be None or string
    gen = slot.get("generator")
    if gen is not None and not isinstance(gen, str):
        errors.append(f"{prefix}.generator must be string or null")
    
    # Params
    params = slot.get("params", {})
    for key in ["frequency", "cutoff", "resonance", "attack", "decay"]:
        val = params.get(key)
        if val is not None:
            val, warning = _coerce_float(val, f"{prefix}.params.{key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0.0 <= val <= 1.0):
                errors.append(f"{prefix}.params.{key} must be 0-1, got {val}")
    
    for i in range(NUM_CUSTOM_PARAMS):
        key = f"custom_{i}"
        val = params.get(key)
        if val is not None:
            val, warning = _coerce_float(val, f"{prefix}.params.{key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0.0 <= val <= 1.0):
                errors.append(f"{prefix}.params.{key} must be 0-1, got {val}")
    
    # Indices
    ft = slot.get("filter_type", 0)
    if not (0 <= ft < FILTER_TYPES):
        errors.append(f"{prefix}.filter_type must be 0-{FILTER_TYPES-1}, got {ft}")
    
    es = slot.get("env_source", 0)
    if not (0 <= es < ENV_SOURCES):
        errors.append(f"{prefix}.env_source must be 0-{ENV_SOURCES-1}, got {es}")
    
    cr = slot.get("clock_rate", 0)
    if not (0 <= cr < CLOCK_RATES):
        errors.append(f"{prefix}.clock_rate must be 0-{CLOCK_RATES-1}, got {cr}")
    
    mc = slot.get("midi_channel", 1)
    if not (0 <= mc <= MIDI_CHANNELS):
        errors.append(f"{prefix}.midi_channel must be 0-{MIDI_CHANNELS}, got {mc}")
    
    return errors, warnings


def _validate_mixer(mixer: dict, strict: bool = False) -> tuple:
    """Validate mixer state including Phase 1 channel strip fields."""
    errors = []
    warnings = []
    
    mv = mixer.get("master_volume", 0.8)
    mv, warning = _coerce_float(mv, "mixer.master_volume")
    if warning:
        warnings.append(warning)
    if mv is not None and not (0.0 <= mv <= 1.0):
        errors.append(f"mixer.master_volume must be 0-1, got {mv}")
    
    channels = mixer.get("channels", [])
    
    # Check channel count
    if len(channels) != NUM_SLOTS:
        if strict:
            errors.append(f"mixer.channels must have exactly {NUM_SLOTS} items, got {len(channels)}")
        else:
            warnings.append(f"mixer.channels has {len(channels)} items, expected {NUM_SLOTS}")
    
    for i, ch in enumerate(channels[:NUM_SLOTS]):
        if not isinstance(ch, dict):
            errors.append(f"mixer.channels[{i}] must be dict")
            continue
        
        prefix = f"mixer.channels[{i}]"
        
        # Volume (0-1)
        vol = ch.get("volume", 0.8)
        vol, warning = _coerce_float(vol, f"{prefix}.volume")
        if warning:
            warnings.append(warning)
        if vol is not None and not (0.0 <= vol <= 1.0):
            errors.append(f"{prefix}.volume must be 0-1, got {vol}")
        
        # Pan (0-1)
        pan = ch.get("pan", 0.5)
        pan, warning = _coerce_float(pan, f"{prefix}.pan")
        if warning:
            warnings.append(warning)
        if pan is not None and not (0.0 <= pan <= 1.0):
            errors.append(f"{prefix}.pan must be 0-1, got {pan}")
        
        # EQ bands (0-200)
        for eq_key in ["eq_hi", "eq_mid", "eq_lo"]:
            val = ch.get(eq_key, 100)
            val, warning = _coerce_int(val, f"{prefix}.{eq_key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0 <= val <= 200):
                errors.append(f"{prefix}.{eq_key} must be 0-200, got {val}")
        
        # Gain index (0-2)
        gain = ch.get("gain", 0)
        gain, warning = _coerce_int(gain, f"{prefix}.gain")
        if warning:
            warnings.append(warning)
        if gain is not None and not (0 <= gain < GAIN_STAGES):
            errors.append(f"{prefix}.gain must be 0-{GAIN_STAGES-1}, got {gain}")
        
        # Sends (0-200)
        for send_key in ["echo_send", "verb_send"]:
            val = ch.get(send_key, 0)
            val, warning = _coerce_int(val, f"{prefix}.{send_key}")
            if warning:
                warnings.append(warning)
            if val is not None and not (0 <= val <= 200):
                errors.append(f"{prefix}.{send_key} must be 0-200, got {val}")
        
        # Cuts (bool)
        for cut_key in ["lo_cut", "hi_cut"]:
            val = ch.get(cut_key, False)
            if not isinstance(val, bool):
                errors.append(f"{prefix}.{cut_key} must be bool, got {type(val).__name__}")
    
    return errors, warnings


def _validate_master(master: dict, strict: bool = False) -> tuple:
    """Validate master section state (Phase 2)."""
    errors = []
    warnings = []
    prefix = "master"
    
    # Volume (0-1)
    vol = master.get("volume", 0.8)
    vol, warning = _coerce_float(vol, f"{prefix}.volume")
    if warning:
        warnings.append(warning)
    if vol is not None and not (0.0 <= vol <= 1.0):
        errors.append(f"{prefix}.volume must be 0-1, got {vol}")
    
    # EQ sliders (0-240)
    for eq_key in ["eq_hi", "eq_mid", "eq_lo"]:
        val = master.get(eq_key, 120)
        val, warning = _coerce_int(val, f"{prefix}.{eq_key}")
        if warning:
            warnings.append(warning)
        if val is not None and not (0 <= val <= 240):
            errors.append(f"{prefix}.{eq_key} must be 0-240, got {val}")
    
    # EQ kills/buttons (0 or 1)
    for btn_key in ["eq_hi_kill", "eq_mid_kill", "eq_lo_kill", "eq_locut", "eq_bypass"]:
        val = master.get(btn_key, 0)
        val, warning = _coerce_int(val, f"{prefix}.{btn_key}")
        if warning:
            warnings.append(warning)
        if val is not None and val not in (0, 1):
            errors.append(f"{prefix}.{btn_key} must be 0 or 1, got {val}")
    
    # Compressor threshold (0-400)
    val = master.get("comp_threshold", 100)
    val, warning = _coerce_int(val, f"{prefix}.comp_threshold")
    if warning:
        warnings.append(warning)
    if val is not None and not (0 <= val <= 400):
        errors.append(f"{prefix}.comp_threshold must be 0-400, got {val}")
    
    # Compressor makeup (0-200)
    val = master.get("comp_makeup", 0)
    val, warning = _coerce_int(val, f"{prefix}.comp_makeup")
    if warning:
        warnings.append(warning)
    if val is not None and not (0 <= val <= 200):
        errors.append(f"{prefix}.comp_makeup must be 0-200, got {val}")
    
    # Compressor ratio index (0-2)
    val = master.get("comp_ratio", 1)
    val, warning = _coerce_int(val, f"{prefix}.comp_ratio")
    if warning:
        warnings.append(warning)
    if val is not None and not (0 <= val < COMP_RATIOS):
        errors.append(f"{prefix}.comp_ratio must be 0-{COMP_RATIOS-1}, got {val}")
    
    # Compressor attack index (0-5)
    val = master.get("comp_attack", 4)
    val, warning = _coerce_int(val, f"{prefix}.comp_attack")
    if warning:
        warnings.append(warning)
    if val is not None and not (0 <= val < COMP_ATTACKS):
        errors.append(f"{prefix}.comp_attack must be 0-{COMP_ATTACKS-1}, got {val}")
    
    # Compressor release index (0-4)
    val = master.get("comp_release", 4)
    val, warning = _coerce_int(val, f"{prefix}.comp_release")
    if warning:
        warnings.append(warning)
    if val is not None and not (0 <= val < COMP_RELEASES):
        errors.append(f"{prefix}.comp_release must be 0-{COMP_RELEASES-1}, got {val}")
    
    # Compressor SC index (0-5)
    val = master.get("comp_sc", 0)
    val, warning = _coerce_int(val, f"{prefix}.comp_sc")
    if warning:
        warnings.append(warning)
    if val is not None and not (0 <= val < COMP_SC_FREQS):
        errors.append(f"{prefix}.comp_sc must be 0-{COMP_SC_FREQS-1}, got {val}")
    
    # Compressor bypass (0 or 1)
    val = master.get("comp_bypass", 0)
    val, warning = _coerce_int(val, f"{prefix}.comp_bypass")
    if warning:
        warnings.append(warning)
    if val is not None and val not in (0, 1):
        errors.append(f"{prefix}.comp_bypass must be 0 or 1, got {val}")
    
    # Limiter ceiling (0-600)
    val = master.get("limiter_ceiling", 590)
    val, warning = _coerce_int(val, f"{prefix}.limiter_ceiling")
    if warning:
        warnings.append(warning)
    if val is not None and not (0 <= val <= 600):
        errors.append(f"{prefix}.limiter_ceiling must be 0-600, got {val}")
    
    # Limiter bypass (0 or 1)
    val = master.get("limiter_bypass", 0)
    val, warning = _coerce_int(val, f"{prefix}.limiter_bypass")
    if warning:
        warnings.append(warning)
    if val is not None and val not in (0, 1):
        errors.append(f"{prefix}.limiter_bypass must be 0 or 1, got {val}")
    
    return errors, warnings


def _validate_mod_sources(mod_sources: dict, strict: bool = False) -> tuple:
    """Validate modulation sources state (Phase 3)."""
    errors = []
    warnings = []
    
    slots = mod_sources.get("slots", [])
    
    # Check slot count
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
