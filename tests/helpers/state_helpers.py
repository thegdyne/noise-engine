"""
Test helpers for state integrity testing.

autofill_nondefaults() — constructs a dataclass instance with guaranteed
non-default values for every field. Used by round-trip tests so new fields
are automatically covered without manual test updates.

schema_field_names() — returns the set of field names for a dataclass.
Used in both tests and save-time assertions (single definition, no divergence).
"""
from dataclasses import fields, MISSING


# Fields that need structure-aware non-defaults (list-of-dict, etc.)
# Key format: "ClassName.field_name" for class-specific, or bare "field_name" for global
_LIST_FIELD_OVERRIDES = {
    "seq_steps": [{"step_type": 0, "note": 60, "velocity": 100}],
    "arp_notes": [60, 64, 67],
}

# Dict fields that need non-empty non-default values
_DICT_FIELD_OVERRIDES = {
    "params": {"test_param": 0.77},
}


def autofill_nondefaults(cls):
    """
    Construct an instance of dataclass `cls` with every field set to
    a deterministic non-default value.

    The value is always different from the field's default, ensuring that
    round-trip tests detect missing serialization (default -> missing ->
    default would silently pass otherwise).
    """
    kwargs = {}
    for f in fields(cls):
        # Check for structure-aware overrides first
        if f.name in _LIST_FIELD_OVERRIDES:
            kwargs[f.name] = list(_LIST_FIELD_OVERRIDES[f.name])
            continue
        if f.name in _DICT_FIELD_OVERRIDES:
            kwargs[f.name] = dict(_DICT_FIELD_OVERRIDES[f.name])
            continue

        default = _get_default(f)
        ftype = _resolve_type(f.type)

        if ftype == bool:
            kwargs[f.name] = not default if isinstance(default, bool) else True
        elif ftype == float:
            kwargs[f.name] = default + 0.123 if isinstance(default, (int, float)) else 0.42
        elif ftype == int:
            kwargs[f.name] = default + 3 if isinstance(default, int) else 7
        elif ftype == str or f.name == "generator":
            kwargs[f.name] = f"test_{f.name}"
        elif ftype == dict:
            kwargs[f.name] = {"test_key": 42}
        elif ftype == list or "list" in str(f.type).lower():
            # Produce non-default list: shift each element in the default
            if isinstance(default, list) and len(default) > 0:
                kwargs[f.name] = _shift_list(default)
            else:
                kwargs[f.name] = [1]
        else:
            # Optional[str] and similar
            kwargs[f.name] = f"test_{f.name}"
    return cls(**kwargs)


def _shift_list(default_list):
    """Produce a list with every element shifted from its default value."""
    shifted = []
    for v in default_list:
        if isinstance(v, float):
            shifted.append(v + 0.111)
        elif isinstance(v, int):
            shifted.append(v + 1)
        else:
            shifted.append(v)
    return shifted


def schema_field_names(cls):
    """
    Return the set of all field names for dataclass `cls`.

    Used in round-trip tests AND save-time assertions — single definition,
    no divergence possible. Returns raw field names, not JSON keys
    (SlotState nests some fields under "params" in JSON).
    """
    return {f.name for f in fields(cls)}


def _get_default(f):
    """Extract the effective default from a dataclass field."""
    if f.default is not MISSING:
        return f.default
    if f.default_factory is not MISSING:
        return f.default_factory()
    return None


def _resolve_type(annotation) -> type:
    """Best-effort type resolution for simple annotations."""
    if annotation is None:
        return type(None)
    if isinstance(annotation, type):
        return annotation
    origin = getattr(annotation, '__origin__', None)
    if origin is not None:
        return origin
    if isinstance(annotation, str):
        _TYPE_MAP = {"float": float, "int": int, "bool": bool, "str": str}
        return _TYPE_MAP.get(annotation, str)
    return annotation
