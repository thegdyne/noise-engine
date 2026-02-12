"""
Korg .korgmultisample parser.

Parses binary multisample definition files into normalized zone models
for MOLTI-SAMP table construction.

File format: Binary protobuf-like structure (NOT XML).
  - 4-byte "Korg" header
  - 3 length-prefixed chunks (header, metadata, multisample data)
  - Multisample data contains sample zones with key ranges and wav paths

Reference: ConvertWithMoss (github.com/git-moss/ConvertWithMoss)
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from src.utils.logger import logger


@dataclass
class SampleZone:
    """A single sample zone within a multisample."""
    wav_path: str           # Relative path from .korgmultisample file
    low_note: int           # MIDI note range low (0-127)
    high_note: int          # MIDI note range high (0-127)
    root_note: int          # Original pitch of sample
    one_shot: bool = True   # True = one-shot, False = looping
    start: int = 0          # Sample start frame
    end: int = 0            # Sample end frame
    loop_start: int = 0     # Loop start frame
    resolved_path: Optional[Path] = None  # Absolute path after resolution


@dataclass
class MultisampleDef:
    """Parsed multisample definition."""
    name: str
    source_path: Path       # Path to .korgmultisample file
    author: str = ""
    category: str = ""
    comment: str = ""
    zones: List[SampleZone] = field(default_factory=list)

    @property
    def zone_count(self) -> int:
        return len(self.zones)


def _read_varint(data: bytes, pos: int) -> tuple:
    """Read a protobuf-style varint from data at pos."""
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        result |= (b & 0x7f) << shift
        shift += 7
        pos += 1
        if not (b & 0x80):
            break
    return result, pos


def _parse_protobuf_fields(data: bytes) -> list:
    """Parse protobuf-style fields from data.

    Returns list of (field_num, wire_type, value) tuples.
    """
    fields = []
    pos = 0
    while pos < len(data):
        # Tags are varints (can be multi-byte for field numbers > 15)
        tag, pos = _read_varint(data, pos)
        wire_type = tag & 0x07
        field_num = tag >> 3

        if wire_type == 0:  # varint
            val, pos = _read_varint(data, pos)
            fields.append((field_num, 'varint', val))
        elif wire_type == 2:  # length-delimited (bytes/string/nested)
            slen, pos = _read_varint(data, pos)
            sdata = data[pos:pos + slen]
            fields.append((field_num, 'bytes', sdata))
            pos += slen
        elif wire_type == 5:  # 32-bit fixed (float)
            if pos + 4 <= len(data):
                val = struct.unpack('<f', data[pos:pos + 4])[0]
                fields.append((field_num, 'float', val))
            pos += 4
        elif wire_type == 1:  # 64-bit fixed
            pos += 8
        else:
            break  # Unknown wire type — stop parsing this block
    return fields


def _parse_sample_block(block_data: bytes) -> Optional[SampleZone]:
    """Parse a single sample block into a SampleZone.

    Block structure (protobuf-like):
      field 1 (bytes): nested sample data containing wav_path + sample params
      field 2 (varint): key_bottom
      field 3 (varint): key_top
      field 4 (varint): key_original
      field 5 (varint): fixed_pitch
      field 6 (float): tune
      field 7 (float): level_left
      field 8 (float): level_right
      field 10 (varint): color
    """
    outer = _parse_protobuf_fields(block_data)

    wav_path = ""
    one_shot = False
    start = 0
    end = 0
    loop_start = 0
    key_bottom = -1
    key_top = -1
    key_original = -1

    for fnum, ftype, fval in outer:
        if fnum == 1 and ftype == 'bytes':
            # Nested sample data message
            inner = _parse_protobuf_fields(fval)
            for ifnum, iftype, ifval in inner:
                if ifnum == 1 and iftype == 'bytes':
                    wav_path = ifval.decode('utf-8', errors='replace')
                elif ifnum == 2 and iftype == 'varint':
                    start = ifval
                elif ifnum == 3 and iftype == 'varint':
                    loop_start = ifval
                elif ifnum == 4 and iftype == 'varint':
                    end = ifval
                elif ifnum == 9 and iftype == 'varint':
                    one_shot = bool(ifval)
                elif ifnum == 10 and iftype == 'varint':
                    pass  # boost_12db
        elif fnum == 2 and ftype == 'varint':
            key_bottom = fval
        elif fnum == 3 and ftype == 'varint':
            key_top = fval
        elif fnum == 4 and ftype == 'varint':
            key_original = fval

    if not wav_path:
        return None

    # If key zone not specified, use root_note=0, full range
    # (sample 0 in the test file has no key zone — it maps to note 0)
    if key_bottom < 0:
        key_bottom = 0
    if key_top < 0:
        key_top = key_bottom
    if key_original < 0:
        key_original = key_bottom

    return SampleZone(
        wav_path=wav_path,
        low_note=key_bottom,
        high_note=key_top,
        root_note=key_original,
        one_shot=one_shot,
        start=start,
        end=end,
        loop_start=loop_start,
    )


def parse_korgmultisample(filepath) -> MultisampleDef:
    """
    Parse a .korgmultisample file.

    Args:
        filepath: Path to .korgmultisample file

    Returns:
        MultisampleDef with zones extracted

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file cannot be parsed
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Multisample not found: {filepath}")

    with open(filepath, 'rb') as f:
        data = f.read()

    # Validate header
    if len(data) < 4 or data[:4] != b'Korg':
        raise ValueError(f"Not a valid .korgmultisample file (missing Korg header): {filepath}")

    pos = 4

    # Skip chunk 1 (header info) and chunk 2 (metadata)
    for _ in range(2):
        if pos + 4 > len(data):
            raise ValueError(f"Truncated .korgmultisample file: {filepath}")
        chunk_size = struct.unpack('<I', data[pos:pos + 4])[0]
        pos += 4 + chunk_size

    # Read chunk 3 (multisample data)
    if pos + 4 > len(data):
        raise ValueError(f"Missing multisample data chunk: {filepath}")
    chunk3_size = struct.unpack('<I', data[pos:pos + 4])[0]
    pos += 4
    chunk3 = data[pos:pos + chunk3_size]

    # Parse multisample metadata fields
    p = 0
    ms_name = filepath.stem
    author = ""
    category = ""
    comment = ""

    # Read metadata fields until we hit sample blocks (field 5, wire 2)
    # Tags are varints — peek-parse to check field number before consuming
    while p < len(chunk3):
        tag, next_p = _read_varint(chunk3, p)
        wire_type = tag & 0x07
        field_num = tag >> 3

        # Sample blocks are field 5 — stop metadata parsing
        if field_num == 5 and wire_type == 2:
            break

        p = next_p  # Consume the tag

        if wire_type == 2:  # length-delimited
            slen, p = _read_varint(chunk3, p)
            sdata = chunk3[p:p + slen]
            p += slen

            if field_num == 1:
                ms_name = sdata.decode('utf-8', errors='replace')
            elif field_num == 2:
                author = sdata.decode('utf-8', errors='replace')
            elif field_num == 3:
                category = sdata.decode('utf-8', errors='replace')
            elif field_num == 4:
                comment = sdata.decode('utf-8', errors='replace')
            elif field_num == 7:
                pass  # UUID
        elif wire_type == 0:
            _, p = _read_varint(chunk3, p)
        elif wire_type == 5:
            p += 4
        elif wire_type == 1:
            p += 8
        else:
            break  # Unknown wire type

    # Parse sample blocks (field 5, wire 2 — tag is varint)
    zones = []
    while p < len(chunk3):
        tag, next_p = _read_varint(chunk3, p)
        wire_type = tag & 0x07
        field_num = tag >> 3

        if field_num != 5 or wire_type != 2:
            break

        p = next_p
        block_len, p = _read_varint(chunk3, p)
        block = chunk3[p:p + block_len]

        zone = _parse_sample_block(block)
        if zone:
            zones.append(zone)

        p += block_len

    msdef = MultisampleDef(
        name=ms_name,
        source_path=filepath,
        author=author,
        category=category,
        comment=comment,
        zones=zones,
    )

    logger.info(
        f"[MOLTI] Parsed '{ms_name}': {len(zones)} zones, "
        f"author='{author}', category='{category}'",
        component="MOLTI"
    )

    return msdef


def resolve_sample_paths(
    msdef: MultisampleDef,
    sample_roots: Optional[List[Path]] = None
) -> List[str]:
    """
    Resolve wav paths to absolute filesystem paths.

    Resolution order (per spec):
        1. ms_path.parent / wav_path
        2. Path.home() / wav_path
        3. For each root in sample_roots: root / wav_path
        4. Fail with list of attempted paths

    Args:
        msdef: Parsed multisample definition
        sample_roots: Additional search directories

    Returns:
        List of error messages (empty = all resolved OK)
    """
    errors = []
    ms_dir = msdef.source_path.parent

    for zone in msdef.zones:
        wav_path = zone.wav_path
        attempted = []

        # Try resolution order
        candidates = [ms_dir / wav_path, Path.home() / wav_path]
        if sample_roots:
            candidates.extend(root / wav_path for root in sample_roots)

        resolved = None
        for candidate in candidates:
            attempted.append(str(candidate))
            if candidate.exists():
                resolved = candidate
                break

        if resolved:
            zone.resolved_path = resolved
        else:
            errors.append(
                f"Sample not found: {wav_path}\n"
                f"  Tried: {', '.join(attempted)}"
            )

    return errors


def build_note_map(zones: List[SampleZone]) -> List[int]:
    """
    Build MIDI note -> zone index mapping (128 entries).

    Notes outside any zone map to -1.
    Overlapping zones: lowest-indexed zone wins.

    Returns:
        List of 128 ints (zone indices, -1 for unmapped)
    """
    note_map = [-1] * 128

    for zone_idx, zone in enumerate(zones):
        for note in range(zone.low_note, zone.high_note + 1):
            if 0 <= note <= 127 and note_map[note] == -1:
                note_map[note] = zone_idx

    return note_map
