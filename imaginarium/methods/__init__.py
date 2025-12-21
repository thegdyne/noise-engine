"""
imaginarium/methods/__init__.py
Method registry - discovers and loads synthesis templates
"""

from typing import Dict, List, Optional
from .base import MethodTemplate, MethodDefinition

# Global registry
_REGISTRY: Dict[str, MethodTemplate] = {}


def register_method(template: MethodTemplate) -> None:
    """Register a method template."""
    method_id = template.definition.method_id
    if method_id in _REGISTRY:
        raise ValueError(f"Method {method_id} already registered")
    _REGISTRY[method_id] = template


def get_method(method_id: str) -> Optional[MethodTemplate]:
    """Get a registered method by ID."""
    return _REGISTRY.get(method_id)


def list_methods() -> List[str]:
    """List all registered method IDs."""
    return list(_REGISTRY.keys())


def list_methods_by_family(family: str) -> List[str]:
    """List method IDs for a specific family."""
    return [
        mid for mid, template in _REGISTRY.items()
        if template.definition.family == family
    ]


def get_all_methods() -> Dict[str, MethodTemplate]:
    """Get all registered methods."""
    return dict(_REGISTRY)


# =============================================================================
# Auto-registration of built-in methods
# =============================================================================

def _register_builtins():
    """Register all built-in method templates."""
    # Import here to avoid circular imports
    from .subtractive.bright_saw import BrightSawTemplate
    from .subtractive.dark_pulse import DarkPulseTemplate
    from .fm.simple_fm import SimpleFMTemplate
    from .physical.karplus import KarplusTemplate
    
    register_method(BrightSawTemplate())
    register_method(DarkPulseTemplate())
    register_method(SimpleFMTemplate())
    register_method(KarplusTemplate())


# Register on import
_register_builtins()
