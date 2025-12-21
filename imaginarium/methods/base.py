"""
imaginarium/methods/base.py
Base class for synthesis method templates

Each method defines:
- Parameter axes (what can vary)
- Macro controls (how params map to musical concepts)
- SynthDef template (Jinja2 or string interpolation)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ParamAxis:
    """A parameter that can vary in candidate generation."""
    name: str
    min_val: float
    max_val: float
    default: float
    curve: str = "lin"  # "lin" or "exp"
    
    def sample(self, t: float) -> float:
        """
        Sample parameter at position t (0-1).
        
        Args:
            t: Position in range [0, 1]
        
        Returns:
            Parameter value
        """
        if self.curve == "exp":
            # Exponential interpolation
            return self.min_val * ((self.max_val / self.min_val) ** t)
        else:
            # Linear interpolation
            return self.min_val + t * (self.max_val - self.min_val)


@dataclass
class MacroControl:
    """
    A macro control maps a single 0-1 value to multiple parameters.
    
    Used to explore the parameter space more efficiently by coupling
    related parameters (e.g., "BRIGHTNESS" controls cutoff + drive).
    """
    name: str  # e.g., "TONE", "EDGE", "MOTION"
    param_weights: Dict[str, float] = field(default_factory=dict)
    # Maps param name -> weight (positive = increase with macro, negative = decrease)


@dataclass
class MethodDefinition:
    """
    Complete definition of a synthesis method.
    
    Corresponds to IMAGINARIUM_SPEC §5.2
    """
    method_id: str           # e.g., "subtractive/bright_saw"
    family: str              # e.g., "subtractive"
    display_name: str        # e.g., "Bright Saw"
    template_version: str    # For candidate_id stability
    
    param_axes: List[ParamAxis] = field(default_factory=list)
    macro_controls: List[MacroControl] = field(default_factory=list)
    
    # Default tags (method-level, candidates may add more)
    default_tags: Dict[str, str] = field(default_factory=dict)


class MethodTemplate(ABC):
    """
    Abstract base class for synthesis method templates.
    
    Subclasses implement specific synthesis approaches (e.g., bright_saw, simple_fm).
    """
    
    @property
    @abstractmethod
    def definition(self) -> MethodDefinition:
        """Return the method definition."""
        pass
    
    @abstractmethod
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        """
        Generate SuperCollider SynthDef code.
        
        Args:
            synthdef_name: Unique name for this SynthDef (e.g., "imaginarium_pack_method_001")
            params: Parameter values from param_axes
            seed: Seed value to embed in SynthDef
        
        Returns:
            Complete SynthDef code as string
        """
        pass
    
    @abstractmethod
    def generate_json(
        self,
        display_name: str,
        synthdef_name: str,
    ) -> dict:
        """
        Generate generator JSON config.
        
        Args:
            display_name: Human-readable name for UI
            synthdef_name: Must match SynthDef name
        
        Returns:
            Generator config dict (per GENERATOR_SPEC.md)
        """
        pass
    
    def generate_candidate_id(
        self,
        macro_name: str,
        param_index: int,
    ) -> str:
        """
        Generate stable candidate ID.
        
        Format: "{method_id}:{macro}:{param_index}:{template_version}"
        """
        d = self.definition
        return f"{d.method_id}:{macro_name}:{param_index}:{d.template_version}"
    
    def sample_params(
        self,
        macro_values: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Sample parameter values from macro controls.
        
        Args:
            macro_values: Dict of macro name -> value (0-1)
        
        Returns:
            Dict of param name -> sampled value
        """
        d = self.definition
        params = {}
        
        # Start with axis defaults
        for axis in d.param_axes:
            params[axis.name] = axis.default
        
        # Apply macro controls
        for macro in d.macro_controls:
            if macro.name not in macro_values:
                continue
            macro_val = macro_values[macro.name]
            
            for param_name, weight in macro.param_weights.items():
                # Find axis
                axis = next((a for a in d.param_axes if a.name == param_name), None)
                if axis is None:
                    continue
                
                # Weighted blend toward macro value
                t = macro_val if weight > 0 else (1.0 - macro_val)
                blended = axis.sample(t)
                
                # Mix with current value based on weight magnitude
                w = abs(weight)
                params[param_name] = params[param_name] * (1 - w) + blended * w
        
        return params
    
    def get_tags(self, params: Dict[str, float]) -> Dict[str, str]:
        """
        Generate tags for a candidate based on its parameters.
        
        Subclasses can override to add parameter-dependent tags.
        """
        tags = dict(self.definition.default_tags)
        tags["family"] = self.definition.family
        tags["method"] = self.definition.method_id
        return tags
