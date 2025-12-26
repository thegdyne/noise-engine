"""
imaginarium/naming.py
Centralized naming schema for Noise Engine packs

Naming Convention (per CQD_FORGE_SPEC.md v1.0):
- pack_id:       [a-z][a-z0-9_]*  (max 24 chars, slug)
- generator_id:  [a-z][a-z0-9_]*  (max 24 chars, slug)
- synthdef:      forge_{pack_id}_{generator_id}  (max 56 chars)
- generator_ref: {pack_id}:{generator_id}

For Imaginarium-generated packs:
- synthdef:      imaginarium_{pack_id}_{method}_{index}
"""

import re
from typing import Tuple

# Validation patterns
PACK_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]*$")
GENERATOR_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]*$")

# Reserved pack IDs (would collide with core namespaces)
RESERVED_PACK_IDS = frozenset({
    "core", "mod", "test",
})

# Length limits
MAX_PACK_ID_LENGTH = 24
MAX_GENERATOR_ID_LENGTH = 24
MAX_SYNTHDEF_LENGTH = 56


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
    
    return slug


def validate_pack_id(pack_id: str) -> None:
    """
    Validate pack_id or raise NamingError.
    
    Rules:
    - Lowercase letters, digits, underscores only
    - Must start with letter
    - Max 24 characters
    - Not a reserved name
    """
    if not pack_id:
        raise NamingError("pack_id cannot be empty")
    
    if not PACK_ID_REGEX.match(pack_id):
        raise NamingError(
            f"pack_id '{pack_id}' must be lowercase slug "
            "(letters, digits, underscores; start with letter)"
        )
    
    if len(pack_id) > MAX_PACK_ID_LENGTH:
        raise NamingError(
            f"pack_id '{pack_id}' exceeds {MAX_PACK_ID_LENGTH} characters"
        )
    
    if pack_id in RESERVED_PACK_IDS:
        raise NamingError(f"pack_id '{pack_id}' is reserved")


def validate_generator_id(generator_id: str) -> None:
    """
    Validate generator_id or raise NamingError.
    
    Rules:
    - Lowercase letters, digits, underscores only
    - Must start with letter
    - Max 24 characters
    """
    if not generator_id:
        raise NamingError("generator_id cannot be empty")
    
    if not GENERATOR_ID_REGEX.match(generator_id):
        raise NamingError(
            f"generator_id '{generator_id}' must be lowercase slug "
            "(letters, digits, underscores; start with letter)"
        )
    
    if len(generator_id) > MAX_GENERATOR_ID_LENGTH:
        raise NamingError(
            f"generator_id '{generator_id}' exceeds {MAX_GENERATOR_ID_LENGTH} characters"
        )


def make_synthdef_name(pack_id: str, generator_id: str, prefix: str = "forge") -> str:
    """
    Generate synthdef name: {prefix}_{pack_id}_{generator_id}
    
    Default prefix is 'forge' for CQD_Forge packs.
    Use 'imaginarium' for auto-generated packs.
    """
    validate_pack_id(pack_id)
    validate_generator_id(generator_id)
    
    synthdef = f"{prefix}_{pack_id}_{generator_id}"
    
    if len(synthdef) > MAX_SYNTHDEF_LENGTH:
        raise NamingError(
            f"synthdef name '{synthdef}' exceeds {MAX_SYNTHDEF_LENGTH} characters"
        )
    
    return synthdef


def make_generator_ref(pack_id: str, generator_id: str) -> str:
    """
    Generate generator reference: {pack_id}:{generator_id}
    
    Used in preset files to reference generators.
    """
    validate_pack_id(pack_id)
    validate_generator_id(generator_id)
    return f"{pack_id}:{generator_id}"


def parse_generator_ref(ref: str) -> Tuple[str, str]:
    """
    Parse generator reference into (pack_id, generator_id).
    
    Raises NamingError if format is invalid.
    """
    if ":" not in ref:
        raise NamingError(f"Invalid generator_ref '{ref}': missing ':'")
    
    parts = ref.split(":", 1)
    if len(parts) != 2:
        raise NamingError(f"Invalid generator_ref '{ref}': expected 'pack:gen'")
    
    pack_id, generator_id = parts
    validate_pack_id(pack_id)
    validate_generator_id(generator_id)
    
    return pack_id, generator_id


def make_generator_id_from_method(method_id: str, index: int) -> str:
    """
    Generate generator_id from method_id and slot index.

    Args:
        method_id: Method identifier like "fm/basic_fm"
        index: Slot index (0-7)

    Returns:
        Valid generator_id like "basic_fm_0"
    """
    # Extract method name from "family/method_name"
    if "/" in method_id:
        method_name = method_id.split("/")[-1]
    else:
        method_name = method_id

    # Build generator_id with index suffix (leave room for "_N")
    base = sanitize_to_slug(method_name, max_length=MAX_GENERATOR_ID_LENGTH - 2)
    generator_id = f"{base}_{index}"

    validate_generator_id(generator_id)
    return generator_id


