"""
Preset schema definition and validation.
v2 - Phase 1: Channel strip expansion (EQ, gain, sends, cuts)
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
class MixerState:
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
    slots: list = field(default_factory=lambda: [SlotState() for _ in range(NUM_SLOTS)])
    mixer: MixerState = field(default_factory=MixerState)
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "mapping_version": self.mapping_version,
            "name": self.name,
            "created": self.created,
            "slots": [slot.to_dict() for slot in self.slots],
            "mixer": self.mixer.to_dict(),
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
            slots=slots[:NUM_SLOTS],
            mixer=MixerState.from_dict(data.get("mixer", {})),
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


def validate_preset(data: dict, strict: bool = False) -> tuple[bool, list[str]]:
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
    
    if strict and (errors or warnings):
        raise PresetValidationError(errors + warnings)
    
    return len(errors) == 0, errors + warnings


def _validate_slot(slot: dict, index: int, strict: bool = False) -> tuple[list[str], list[str]]:
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


def _validate_mixer(mixer: dict, strict: bool = False) -> tuple[list[str], list[str]]:
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
