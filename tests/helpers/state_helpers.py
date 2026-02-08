"""
Test helpers for state integrity testing.

autofill_nondefaults() — constructs a dataclass instance with guaranteed
non-default values for every field. Used by round-trip tests so new fields
are automatically covered without manual test updates.

schema_keys() — returns the set of JSON keys that to_dict() must emit.
Used in both tests and save-time assertions (single definition, no divergence).
"""
from dataclasses import fields, MISSING


# Fields that need structure-aware non-defaults (list-of-dict, etc.)
_LIST_FIELD_OVERRIDES = {
    "seq_steps": [{"step_type": 0, "note": 60, "velocity": 100}],
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
        elif ftype == list or "list" in str(f.type).lower():
            # Generic list fallback: emit a simple primitive list
            kwargs[f.name] = [1]
        else:
            # Optional[str] and similar
            kwargs[f.name] = f"test_{f.name}"
    return cls(**kwargs)


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
