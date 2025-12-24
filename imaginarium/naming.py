"""
imaginarium/naming.py
Centralized naming schema for Noise Engine packs

Naming Convention:
- pack_id:       [a-z][a-z0-9_]{2,23}  (3-24 chars, slug)
- generator_id:  [a-z][a-z0-9_]{0,31}  (1-32 chars, slug)
- synthdef:      ne_{pack_id}__{generator_id}  (max 64 chars)
- generator_ref: {pack_id}:{generator_id}

Rules:
- '__' (double underscore) forbidden in IDs (reserved as separator)
- pack_id is immutable once published
- synthdef names are derived, never authored
"""

import re
from typing import Tuple

# Validation patterns
PACK_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]{2,23}$")
GENERATOR_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

# Reserved pack IDs (would collide with core namespaces)
RESERVED_PACK_IDS = frozenset({
    "core", "mod", "default", "factory", "test", "user", "tmp", "null",
})

# Length limits
MAX_PACK_ID_LENGTH = 24
MAX_GENERATOR_ID_LENGTH = 32
MAX_SYNTHDEF_LENGTH = 64


class NamingError(ValueError):
    """Raised when a name violates the naming schema."""
    pass


def sanitize_to_slug(name: str, max_length: int = 24) -> str:
    """
    Convert arbitrary string to valid slug.
    
    - Lowercase
    - Replace non-alphanumeric with underscore
    - Collapse multiple underscores
    - Strip leading/trailing underscores
    - Ensure starts with letter
    - Truncate to max_length
    """
    # Lowercase and replace invalid chars
    slug = "".join(c if c.isalnum() else "_" for c in name.lower())
    
    # Collapse multiple underscores
    while "__" in slug:
        slug = slug.replace("__", "_")
    
    # Strip leading/trailing underscores
    slug = slug.strip("_")
    
    # Ensure starts with letter
    if slug and not slug[0].isalpha():
        slug = "x" + slug
    
    # Truncate
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("_")
    
    # Minimum length
    if len(slug) < 1:
        slug = "unnamed"
    
    # Ensure minimum 3 chars for pack_id compatibility
    while len(slug) < 3:
        slug = slug + "x"
    
    return slug


def validate_pack_id(pack_id: str) -> None:
    """
    Validate pack_id against schema rules.
    
    Raises:
        NamingError: If validation fails
    """
    if "__" in pack_id:
        raise NamingError(f"pack_id '{pack_id}' may not contain '__' (reserved separator)")
    
    if pack_id in RESERVED_PACK_IDS:
        raise NamingError(f"pack_id '{pack_id}' is reserved")
    
    if not PACK_ID_REGEX.fullmatch(pack_id):
        raise NamingError(
            f"pack_id '{pack_id}' must match ^[a-z][a-z0-9_]{{2,23}}$ "
            f"(3-24 chars, lowercase, start with letter)"
        )


def validate_generator_id(generator_id: str) -> None:
    """
    Validate generator_id against schema rules.
    
    Raises:
        NamingError: If validation fails
    """
    if "__" in generator_id:
        raise NamingError(f"generator_id '{generator_id}' may not contain '__' (reserved separator)")
    
    if not GENERATOR_ID_REGEX.fullmatch(generator_id):
        raise NamingError(
            f"generator_id '{generator_id}' must match ^[a-z][a-z0-9_]{{0,31}}$ "
            f"(1-32 chars, lowercase, start with letter)"
        )


def make_synthdef_name(pack_id: str, generator_id: str) -> str:
    """
    Generate SynthDef name from pack_id and generator_id.
    
    Format: ne_{pack_id}__{generator_id}
    
    Args:
        pack_id: Validated pack ID
        generator_id: Validated generator ID
        
    Returns:
        SynthDef name string
        
    Raises:
        NamingError: If inputs invalid or result exceeds 64 chars
    """
    validate_pack_id(pack_id)
    validate_generator_id(generator_id)
    
    name = f"ne_{pack_id}__{generator_id}"
    
    if len(name) > MAX_SYNTHDEF_LENGTH:
        raise NamingError(
            f"synthdef '{name}' is {len(name)} chars (max {MAX_SYNTHDEF_LENGTH})"
        )
    
    return name


def make_generator_ref(pack_id: str, generator_id: str) -> str:
    """
    Generate generator reference string for presets.
    
    Format: {pack_id}:{generator_id}
    
    Args:
        pack_id: Validated pack ID
        generator_id: Validated generator ID
        
    Returns:
        Generator reference string
    """
    validate_pack_id(pack_id)
    validate_generator_id(generator_id)
    return f"{pack_id}:{generator_id}"


def parse_synthdef_name(synthdef: str) -> Tuple[str, str]:
    """
    Parse SynthDef name back to pack_id and generator_id.
    
    Args:
        synthdef: SynthDef name in ne_{pack_id}__{generator_id} format
        
    Returns:
        Tuple of (pack_id, generator_id)
        
    Raises:
        NamingError: If format invalid
    """
    if not synthdef.startswith("ne_"):
        raise NamingError(f"synthdef '{synthdef}' must start with 'ne_'")
    
    remainder = synthdef[3:]  # Strip "ne_"
    
    if "__" not in remainder:
        raise NamingError(f"synthdef '{synthdef}' missing '__' separator")
    
    pack_id, generator_id = remainder.split("__", 1)
    
    validate_pack_id(pack_id)
    validate_generator_id(generator_id)
    
    return pack_id, generator_id


def parse_generator_ref(ref: str) -> Tuple[str, str]:
    """
    Parse generator reference back to pack_id and generator_id.
    
    Args:
        ref: Reference in {pack_id}:{generator_id} format
        
    Returns:
        Tuple of (pack_id, generator_id)
        
    Raises:
        NamingError: If format invalid
    """
    if ":" not in ref:
        raise NamingError(f"generator_ref '{ref}' missing ':' separator")
    
    pack_id, generator_id = ref.split(":", 1)
    
    validate_pack_id(pack_id)
    validate_generator_id(generator_id)
    
    return pack_id, generator_id


def make_generator_id_from_method(method_id: str, index: int) -> str:
    """
    Generate a generator_id from method name and slot index.
    
    Used by Imaginarium to create generator IDs for auto-generated packs.
    
    Args:
        method_id: Method ID like "subtractive/bright_saw"
        index: Slot index (0-7)
        
    Returns:
        Valid generator_id like "bright_saw_0"
    """
    # Extract method name from path
    method_name = method_id.split("/")[-1] if "/" in method_id else method_id
    
    # Sanitize (leave room for _N suffix)
    base = sanitize_to_slug(method_name, max_length=28)
    
    # Ensure base is at least 1 char
    if not base or len(base) < 1:
        base = "gen"
    
    generator_id = f"{base}_{index}"
    
    # Validate (should always pass given sanitize logic, but belt-and-suspenders)
    validate_generator_id(generator_id)
    
    return generator_id


def is_valid_pack_id(pack_id: str) -> bool:
    """Check if pack_id is valid without raising."""
    try:
        validate_pack_id(pack_id)
        return True
    except NamingError:
        return False


def is_valid_generator_id(generator_id: str) -> bool:
    """Check if generator_id is valid without raising."""
    try:
        validate_generator_id(generator_id)
        return True
    except NamingError:
        return False
