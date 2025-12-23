#!/usr/bin/env python3
"""
imaginarium/validate_methods.py
Validator for Imaginarium method compliance per IMAGINARIUM_CUSTOM_PARAMS_SPEC.md

Checks:
- R1, R10, R11: Axis metadata (label, tooltip, unit)
- R9: Curve safety (exp requires positive min/max)
- R7: Round-trip tolerance for normalize/denormalize
- R3, R8, R13: JSON generation (5 entries, placeholders, key=axis.name)
- R2, R12: SynthDef wiring via IMAG_CUSTOMBUS markers

Usage:
    python -m imaginarium.validate_methods
    
Exit codes:
    0 = all methods pass
    1 = one or more methods fail
"""

import re
import sys
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of validating a single method."""
    method_id: str
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_axis_metadata(method_id: str, axes: list) -> List[str]:
    """
    Check R1, R10, R11: axis metadata requirements.
    
    - label: exactly 3 chars, uppercase A-Z or 0-9
    - label: unique within method
    - tooltip: non-empty for exposed axes
    - unit: allowed empty
    """
    errors = []
    labels_seen = set()
    
    for i, axis in enumerate(axes[:5]):  # Only first 5 are exposed
        # R10: label format
        if not axis.label:
            errors.append(f"Axis '{axis.name}': missing label")
        elif len(axis.label) != 3:
            errors.append(f"Axis '{axis.name}': label '{axis.label}' not 3 chars")
        elif not re.match(r'^[A-Z0-9]{3}$', axis.label):
            errors.append(f"Axis '{axis.name}': label '{axis.label}' must be uppercase A-Z/0-9")
        
        # R10: label uniqueness
        if axis.label in labels_seen:
            errors.append(f"Axis '{axis.name}': duplicate label '{axis.label}'")
        labels_seen.add(axis.label)
        
        # R11: tooltip required
        if not axis.tooltip:
            errors.append(f"Axis '{axis.name}': missing tooltip (R11)")
    
    return errors


def validate_curve_safety(method_id: str, axes: list) -> List[str]:
    """
    Check R9: curve safety.
    
    - min_val < max_val
    - exp curve requires min_val > 0 and max_val > 0
    """
    errors = []
    
    for axis in axes:
        if axis.min_val >= axis.max_val:
            errors.append(f"Axis '{axis.name}': min_val >= max_val ({axis.min_val} >= {axis.max_val})")
        
        if axis.curve == "exp":
            if axis.min_val <= 0:
                errors.append(f"Axis '{axis.name}': exp curve requires min_val > 0 (got {axis.min_val})")
            if axis.max_val <= 0:
                errors.append(f"Axis '{axis.name}': exp curve requires max_val > 0 (got {axis.max_val})")
    
    return errors


def validate_round_trip(method_id: str, axes: list) -> List[str]:
    """
    Check R7: normalize/denormalize round-trip.
    
    Test representative values: min, max, default.
    Tolerances:
    - lin: absolute tolerance 1e-6 * (max-min)
    - exp: relative tolerance 1e-6
    """
    errors = []
    
    for axis in axes[:5]:
        test_values = [axis.min_val, axis.max_val, axis.default]
        
        for val in test_values:
            try:
                norm = axis.normalize(val)
                denorm = axis.denormalize(norm)
                
                if axis.curve == "lin":
                    tol = 1e-6 * (axis.max_val - axis.min_val)
                    if abs(denorm - val) > tol:
                        errors.append(
                            f"Axis '{axis.name}': round-trip failed for {val} "
                            f"(got {denorm}, diff={abs(denorm - val)}, tol={tol})"
                        )
                else:  # exp
                    if val > 0:  # Can only check positive values for exp
                        rel_diff = abs(denorm - val) / val
                        if rel_diff > 1e-6:
                            errors.append(
                                f"Axis '{axis.name}': round-trip failed for {val} "
                                f"(got {denorm}, rel_diff={rel_diff})"
                            )
            except Exception as e:
                errors.append(f"Axis '{axis.name}': round-trip exception for {val}: {e}")
    
    return errors


def validate_json_generation(method_id: str, template) -> List[str]:
    """
    Check R3, R8, R13: JSON generation requirements.
    
    - R3: exactly 5 custom_params entries
    - R13: key equals axis.name for exposed axes
    - R8: placeholder schema for unused slots
    """
    errors = []
    
    try:
        result = template.generate_json("Test", "test_synth", params={})
    except Exception as e:
        errors.append(f"generate_json() raised exception: {e}")
        return errors
    
    custom_params = result.get("custom_params", [])
    
    # R3: exactly 5 entries
    if len(custom_params) != 5:
        errors.append(f"custom_params has {len(custom_params)} entries, expected 5 (R3)")
        return errors  # Can't check further if wrong count
    
    axes = template.definition.param_axes[:5]
    n_axes = len(axes)
    
    # Check exposed axes
    for i, axis in enumerate(axes):
        cp = custom_params[i]
        
        # Required fields
        required = ["key", "label", "tooltip", "default", "min", "max", "curve", "unit"]
        for field in required:
            if field not in cp:
                errors.append(f"custom_params[{i}] missing field '{field}'")
        
        # R13: key equals axis.name
        if cp.get("key") != axis.name:
            errors.append(f"custom_params[{i}] key '{cp.get('key')}' != axis.name '{axis.name}' (R13)")
        
        # Default in range
        default = cp.get("default", -1)
        if not (0.0 <= default <= 1.0):
            errors.append(f"custom_params[{i}] default {default} not in [0, 1]")
        
        # Fixed min/max/curve
        if cp.get("min") != 0.0:
            errors.append(f"custom_params[{i}] min != 0.0")
        if cp.get("max") != 1.0:
            errors.append(f"custom_params[{i}] max != 1.0")
        if cp.get("curve") != "lin":
            errors.append(f"custom_params[{i}] curve != 'lin'")
    
    # R8: Check placeholders
    for i in range(n_axes, 5):
        cp = custom_params[i]
        
        if cp.get("key") != f"unused_{i}":
            errors.append(f"custom_params[{i}] placeholder key != 'unused_{i}' (R8)")
        if cp.get("label") != "---":
            errors.append(f"custom_params[{i}] placeholder label != '---' (R8)")
        if cp.get("tooltip") != "":
            errors.append(f"custom_params[{i}] placeholder tooltip != '' (R8)")
        if cp.get("default") != 0.5:
            errors.append(f"custom_params[{i}] placeholder default != 0.5 (R8)")
    
    return errors


def validate_synthdef_markers(method_id: str, template) -> List[str]:
    """
    Check R2, R12: SynthDef wiring via IMAG_CUSTOMBUS markers.
    
    For N exposed axes (max 5), SynthDef must contain markers:
    - IMAG_CUSTOMBUS:0 ... IMAG_CUSTOMBUS:N-1
    """
    errors = []
    
    try:
        scd = template.generate_synthdef("test_synth", {}, seed=12345)
    except Exception as e:
        errors.append(f"generate_synthdef() raised exception: {e}")
        return errors
    
    n_axes = min(len(template.definition.param_axes), 5)
    
    for i in range(n_axes):
        marker = f"/// IMAG_CUSTOMBUS:{i}"
        if marker not in scd:
            errors.append(f"Missing marker '{marker}' in SynthDef (R2, R12)")
    
    return errors


def validate_method(template) -> ValidationResult:
    """Validate a single method template."""
    method_id = template.definition.method_id
    axes = template.definition.param_axes
    
    all_errors = []
    
    # Run all checks
    all_errors.extend(validate_axis_metadata(method_id, axes))
    all_errors.extend(validate_curve_safety(method_id, axes))
    all_errors.extend(validate_round_trip(method_id, axes))
    all_errors.extend(validate_json_generation(method_id, template))
    all_errors.extend(validate_synthdef_markers(method_id, template))
    
    return ValidationResult(
        method_id=method_id,
        passed=len(all_errors) == 0,
        errors=all_errors,
    )


def validate_all_methods() -> Tuple[int, int, List[ValidationResult]]:
    """
    Validate all registered methods.

    Called by generate.py for R6 validation gate.

    Returns:
        Tuple of (passed_count, failed_count, list of ValidationResults)
    """
    from imaginarium.methods import get_all_methods

    methods = get_all_methods()

    if not methods:
        return (0, 0, [])

    results: List[ValidationResult] = []

    for method_id, template in sorted(methods.items()):
        result = validate_method(template)
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    return (passed, failed, results)


def main() -> int:
    """
    Validate all registered methods.
    
    Returns:
        0 if all pass, 1 if any fail
    """
    # Import here to trigger auto-registration
    from imaginarium.methods import get_all_methods
    
    methods = get_all_methods()
    
    if not methods:
        print("ERROR: No methods registered")
        return 1
    
    print(f"Validating {len(methods)} methods...\n")
    
    results: List[ValidationResult] = []
    
    for method_id, template in sorted(methods.items()):
        result = validate_method(template)
        results.append(result)
        
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status}  {method_id}")
        
        if result.errors:
            for error in result.errors:
                print(f"         └─ {error}")
    
    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("\nFailing methods:")
        for r in results:
            if not r.passed:
                print(f"  - {r.method_id} ({len(r.errors)} errors)")
        return 1
    
    print("\nAll methods compliant! ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
