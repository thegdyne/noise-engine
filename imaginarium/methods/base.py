"""
imaginarium/methods/base.py
Base class for synthesis method templates

Each method defines:
- Parameter axes (what can vary)
- Macro controls (how params map to musical concepts)
- SynthDef template (Jinja2 or string interpolation)
"""

import math
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
    
    # Metadata for custom params (R1, R10, R11)
    label: str = ""      # 3-char, e.g., "WID" - required for exposed axes
    tooltip: str = ""    # Human-readable description - required for exposed axes
    unit: str = ""       # Display unit (Hz, ms, dB, etc.) - may be empty
    
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
    
    def normalize(self, value: float) -> float:
        """
        Convert actual value to normalized 0-1 range.
        
        Args:
            value: Actual parameter value in [min_val, max_val]
        
        Returns:
            Normalized value in [0, 1]
        """
        # Clamp to valid range
        value = max(self.min_val, min(self.max_val, value))
        
        if self.curve == "exp":
            # Exponential: n = log(v/min) / log(max/min)
            if self.min_val <= 0 or self.max_val <= 0:
                raise ValueError(f"exp curve requires positive min/max, got {self.min_val}/{self.max_val}")
            return math.log(value / self.min_val) / math.log(self.max_val / self.min_val)
        else:
            # Linear: n = (v - min) / (max - min)
            range_val = self.max_val - self.min_val
            if range_val == 0:
                return 0.5
            return (value - self.min_val) / range_val
    
    def denormalize(self, norm: float) -> float:
        """
        Convert normalized 0-1 value to actual value.
        
        Args:
            norm: Normalized value in [0, 1]
        
        Returns:
            Actual parameter value in [min_val, max_val]
        """
        # Clamp to valid range
        norm = max(0.0, min(1.0, norm))
        
        if self.curve == "exp":
            # Exponential: v = min * (max/min)^n
            if self.min_val <= 0 or self.max_val <= 0:
                raise ValueError(f"exp curve requires positive min/max, got {self.min_val}/{self.max_val}")
            return self.min_val * ((self.max_val / self.min_val) ** norm)
        else:
            # Linear: v = min + n * (max - min)
            return self.min_val + norm * (self.max_val - self.min_val)
    
    def to_custom_param(self, baked_value: float) -> dict:
        """
        Generate custom_param JSON entry per GENERATOR_SPEC.md.
        
        Args:
            baked_value: The actual value to use as default
        
        Returns:
            Dict with key, label, tooltip, default, min, max, curve, unit
        """
        return {
            "key": self.name,  # R13: use axis.name directly
            "label": self.label,
            "tooltip": self.tooltip,
            "default": self.normalize(baked_value),  # R4: normalized
            "min": 0.0,
            "max": 1.0,
            "curve": "lin",  # Always lin in JSON (UI operates in normalized space)
            "unit": self.unit,
        }
    
    def sc_read_expr(self, bus_name: str, axis_index: int) -> str:
        """
        Generate SuperCollider expression to read and denormalize this param.
        
        Emits helper marker token for validation (R12).
        
        Args:
            bus_name: SC bus variable name (e.g., "customBus0")
            axis_index: Index for marker (0-4)
        
        Returns:
            SC code string with marker and mapping expression
        """
        marker = f"/// IMAG_CUSTOMBUS:{axis_index}"
        
        if self.curve == "exp":
            # linexp maps 0-1 to min-max exponentially
            expr = f"In.kr({bus_name}).linexp(0, 1, {self.min_val}, {self.max_val})"
        else:
            # linlin maps 0-1 to min-max linearly
            expr = f"In.kr({bus_name}).linlin(0, 1, {self.min_val}, {self.max_val})"
        
        return f"{marker}\n    {self.name} = {expr};"


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


def _placeholder_custom_param(index: int) -> dict:
    """Generate placeholder custom_param entry for unused slot."""
    return {
        "key": f"unused_{index}",
        "label": "---",
        "tooltip": "",
        "default": 0.5,
        "min": 0.0,
        "max": 1.0,
        "curve": "lin",
        "unit": "",
    }


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
    
    def generate_json(
        self,
        display_name: str,
        synthdef_name: str,
        params: Optional[Dict[str, float]] = None,
    ) -> dict:
        """
        Generate generator JSON config with custom_params.
        
        Args:
            display_name: Human-readable name for UI
            synthdef_name: Must match SynthDef name
            params: Optional baked parameter values for defaults
        
        Returns:
            Generator config dict (per GENERATOR_SPEC.md)
        """
        d = self.definition
        custom_params = []
        axes = d.param_axes[:5]  # Max 5 custom params
        
        # Build entries for exposed axes
        for axis in axes:
            # Use baked value if provided, otherwise axis default
            baked = params.get(axis.name, axis.default) if params else axis.default
            custom_params.append(axis.to_custom_param(baked))
        
        # Fill remaining slots with placeholders (R3: always 5 entries)
        for i in range(len(axes), 5):
            custom_params.append(_placeholder_custom_param(i))
        
        return {
            "name": display_name,
            "synthdef": synthdef_name,
            "custom_params": custom_params,
            "output_trim_db": -6.0,
            "midi_retrig": False,
            "pitch_target": None,
        }
    
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
