"""
imaginarium/export.py
Pack export per IMAGINARIUM_SPEC v10 §16

Exports selected candidates as a Noise Engine pack:
- manifest.json (pack metadata)
- generators/*.json (generator configs)
- generators/*.scd (SynthDef code)
- reports/generation_report.json
- reports/selection_report.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import SPEC_VERSION
from .models import Candidate, SoundSpec, SelectionResult
from .methods import get_method
from .seeds import GenerationContext
from .naming import (
    sanitize_to_slug,
    validate_pack_id,
    make_synthdef_name,
    make_generator_ref,
    make_generator_id_from_method,
    MAX_PACK_ID_LENGTH,
)


def generate_display_name(candidate: Candidate, index: int) -> str:
    """Generate human-readable display name."""
    method = get_method(candidate.method_id)
    if method:
        base = method.definition.display_name
    else:
        base = candidate.method_id.split("/")[-1].replace("_", " ").title()
    return f"{base} {index + 1}"


def export_pack(
    pack_name: str,
    selected: List[Candidate],
    spec: SoundSpec,
    context: GenerationContext,
    input_fingerprint: str,
    output_dir: Path,
    all_candidates: Optional[List[Candidate]] = None,
    selection_result: Optional[SelectionResult] = None,
) -> Path:
    """
    Export selected candidates as a Noise Engine pack.
    
    Args:
        pack_name: Name for the pack (will be sanitized to pack_id)
        selected: Selected candidates to export
        spec: Target SoundSpec
        context: Generation context with seeds
        input_fingerprint: SHA256 of input
        output_dir: Base output directory
        all_candidates: All candidates for report (optional)
        selection_result: Selection result for report (optional)
        
    Returns:
        Path to pack directory
    """
    # Derive pack_id from pack_name
    pack_id = sanitize_to_slug(pack_name, max_length=MAX_PACK_ID_LENGTH)
    validate_pack_id(pack_id)
    
    # Create pack structure
    pack_dir = output_dir / pack_id
    gen_dir = pack_dir / "generators"
    reports_dir = pack_dir / "reports"
    
    pack_dir.mkdir(parents=True, exist_ok=True)
    gen_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)
    
    # Generate files for each selected candidate
    generator_entries = []
    generator_ids = []

    for i, candidate in enumerate(selected):
        # Generate IDs using naming module
        generator_id = make_generator_id_from_method(candidate.method_id, i)
        synthdef_name = make_synthdef_name(pack_id, generator_id)
        display_name = generate_display_name(candidate, i)
        generator_ref = make_generator_ref(pack_id, generator_id)

        method = get_method(candidate.method_id)

        # Generate SynthDef
        if method:
            scd_code = method.generate_synthdef(
                synthdef_name=synthdef_name,
                params=candidate.params,
                seed=candidate.seed,
            )
            json_config = method.generate_json(
                display_name=display_name,
                synthdef_name=synthdef_name,
            )
        else:
            # Fallback for unknown methods
            scd_code = f"// Unknown method: {candidate.method_id}\n"
            json_config = {
                "name": display_name,
                "synthdef": synthdef_name,
                "custom_params": [],
                "output_trim_db": -6.0,
                "midi_retrig": False,
                "pitch_target": None,
            }

        # Add generator_id to JSON config
        json_config["generator_id"] = generator_id

        # Calculate output trim based on measured RMS
        TARGET_RMS_DB = -18.0
        if candidate.features and candidate.features.rms_db > -60:
            trim = TARGET_RMS_DB - candidate.features.rms_db
            trim = max(-18.0, min(18.0, trim))  # Clamp to ±18dB
            json_config["output_trim_db"] = round(float(trim), 1)

        # Write SynthDef (filename = generator_id.scd)
        scd_path = gen_dir / f"{generator_id}.scd"
        scd_path.write_text(scd_code)
        
        # Write generator JSON (filename = generator_id.json)
        json_path = gen_dir / f"{generator_id}.json"
        with open(json_path, "w") as f:
            json.dump(json_config, f, indent=2)
        
        generator_entries.append({
            "generator_id": generator_id,
            "name": display_name,
            "synthdef": synthdef_name,
            "generator_ref": generator_ref,
            "candidate_id": candidate.candidate_id,
            "family": candidate.family,
            "fit_score": candidate.fit_score,
        })
        generator_ids.append(generator_id)
    
    # Write manifest (Noise Engine pack format)
    manifest = {
        "pack_format": 2,
        "pack_id": pack_id,
        "name": pack_name,  # Original display name
        "version": "1.0.0",
        "author": "Imaginarium",
        "description": f"Generated from image (brightness={spec.brightness:.2f}, noisiness={spec.noisiness:.2f})",
        "enabled": True,
        "generators": generator_ids,  # generator_id list
    }
    
    manifest_path = pack_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Write preset (auto-loads all generators into slots 1-8)
    preset = {
        "version": 2,
        "name": pack_name,
        "pack": pack_id,
        "slots": [
            {
                "generator": entry["generator_ref"],  # Use generator_ref format
                "params": {
                    "frequency": 0.5,
                    "cutoff": 1.0,
                    "resonance": 0.0,
                    "attack": 0.0,
                    "decay": 0.76,
                    "custom_0": 0.5,
                    "custom_1": 0.5,
                    "custom_2": 0.5,
                    "custom_3": 0.5,
                    "custom_4": 0.5,
                },
            }
            for entry in generator_entries
        ],
    }

    presets_dir = Path.home() / "noise-engine-presets"
    presets_dir.mkdir(parents=True, exist_ok=True)
    preset_path = presets_dir / f"{pack_id}_preset.json"
    with open(preset_path, "w") as f:
        json.dump(preset, f, indent=2)

    # Write Imaginarium metadata (separate file for traceability)
    imaginarium_meta = {
        "imaginarium_version": SPEC_VERSION,
        "created": datetime.now().isoformat(),
        "input_fingerprint": input_fingerprint,
        "run_seed": context.run_seed,
        "pack_id": pack_id,
        "spec": spec.to_dict(),
        "generator_details": generator_entries,
    }
    
    meta_path = pack_dir / "imaginarium.json"
    with open(meta_path, "w") as f:
        json.dump(imaginarium_meta, f, indent=2)
    
    # Write generation report
    if all_candidates is not None:
        gen_report = {
            "version": SPEC_VERSION,
            "input_fingerprint": input_fingerprint,
            "run_seed": context.run_seed,
            "sobol_seed": context.sobol_seed,
            "pack_id": pack_id,
            "spec": spec.to_dict(),
            "candidates": [
                {
                    "id": c.candidate_id,
                    "seed": c.seed,
                    "method_id": c.method_id,
                    "family": c.family,
                    "fit_score": c.fit_score,
                    "safety_passed": c.safety.passed if c.safety else None,
                    "selected": c.selected,
                }
                for c in all_candidates
            ],
        }
        
        report_path = reports_dir / "generation_report.json"
        with open(report_path, "w") as f:
            json.dump(gen_report, f, indent=2)
    
    # Write selection report
    if selection_result is not None:
        sel_report = {
            "selected": [c.candidate_id for c in selection_result.selected],
            "pairwise_distances": selection_result.pairwise_distances,
            "family_counts": selection_result.family_counts,
            "relaxations_applied": selection_result.relaxations_applied,
            "deadlock": {
                "pool_size": selection_result.deadlock.pool_size,
                "family_counts": selection_result.deadlock.family_counts,
                "constraint_failures": selection_result.deadlock.constraint_failures,
                "relaxation_level": selection_result.deadlock.relaxation_level,
                "fallback_used": selection_result.deadlock.fallback_used,
            } if selection_result.deadlock else None,
        }
        
        report_path = reports_dir / "selection_report.json"
        with open(report_path, "w") as f:
            json.dump(sel_report, f, indent=2)
    
    return pack_dir
