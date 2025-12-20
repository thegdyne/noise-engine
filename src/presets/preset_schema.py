"""
Preset schema definition and validation.
"""

from dataclasses import dataclass, field
from typing import Optional
import json

PRESET_VERSION = 1

# Valid ranges
FILTER_TYPES = 3      # 0=LP, 1=HP, 2=BP
ENV_SOURCES = 3       # 0=OFF, 1=CLK, 2=MIDI  
CLOCK_RATES = 13      # 0-12
MIDI_CHANNELS = 16    # 1-16
NUM_SLOTS = 8
NUM_CUSTOM_PARAMS = 5


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
    volume: float = 0.8
    pan: float = 0.5
    mute: bool = False
    solo: bool = False
    
    def to_dict(self) -> dict:
        return {
            "volume": self.volume,
            "pan": self.pan,
            "mute": self.mute,
            "solo": self.solo,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChannelState":
        return cls(
            volume=data.get("volume", 0.8),
            pan=data.get("pan", 0.5),
            mute=data.get("mute", False),
            solo=data.get("solo", False),
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
    name: str = "Untitled"
    created: str = ""
    slots: list = field(default_factory=lambda: [SlotState() for _ in range(NUM_SLOTS)])
    mixer: MixerState = field(default_factory=MixerState)
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
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


def validate_preset(data: dict) -> tuple[bool, list[str]]:
    """
    Validate preset data structure.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    
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
    elif len(slots) > NUM_SLOTS:
        errors.append(f"Too many slots: {len(slots)} > {NUM_SLOTS}")
    else:
        for i, slot in enumerate(slots):
            slot_errors = _validate_slot(slot, i)
            errors.extend(slot_errors)
    
    # Check mixer
    mixer = data.get("mixer", {})
    if not isinstance(mixer, dict):
        errors.append("mixer must be a dict")
    else:
        mixer_errors = _validate_mixer(mixer)
        errors.extend(mixer_errors)
    
    return len(errors) == 0, errors


def _validate_slot(slot: dict, index: int) -> list[str]:
    """Validate a single slot."""
    errors = []
    prefix = f"slots[{index}]"
    
    # Generator can be None or string
    gen = slot.get("generator")
    if gen is not None and not isinstance(gen, str):
        errors.append(f"{prefix}.generator must be string or null")
    
    # Params
    params = slot.get("params", {})
    for key in ["frequency", "cutoff", "resonance", "attack", "decay"]:
        val = params.get(key)
        if val is not None and not (0.0 <= val <= 1.0):
            errors.append(f"{prefix}.params.{key} must be 0-1, got {val}")
    
    for i in range(NUM_CUSTOM_PARAMS):
        key = f"custom_{i}"
        val = params.get(key)
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
    
    return errors


def _validate_mixer(mixer: dict) -> list[str]:
    """Validate mixer state."""
    errors = []
    
    mv = mixer.get("master_volume", 0.8)
    if not (0.0 <= mv <= 1.0):
        errors.append(f"mixer.master_volume must be 0-1, got {mv}")
    
    channels = mixer.get("channels", [])
    for i, ch in enumerate(channels):
        if not isinstance(ch, dict):
            errors.append(f"mixer.channels[{i}] must be dict")
            continue
        
        vol = ch.get("volume", 0.8)
        if not (0.0 <= vol <= 1.0):
            errors.append(f"mixer.channels[{i}].volume must be 0-1, got {vol}")
        
        pan = ch.get("pan", 0.5)
        if not (0.0 <= pan <= 1.0):
            errors.append(f"mixer.channels[{i}].pan must be 0-1, got {pan}")
    
    return errors
