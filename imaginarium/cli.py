"""
imaginarium/cli.py
Command-line interface for Imaginarium

Usage:
    python -m imaginarium generate --image input.png --name my_pack --seed 42
    python -m imaginarium list-methods
    python -m imaginarium verify --pack packs/my_pack
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .config import PHASE, SPEC_VERSION


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate a pack from input stimulus."""
    from .seeds import GenerationContext
    from .extract import extract_from_image
    from .generate import generate_candidates
    from .methods import list_methods
    from .config import POOL_CONFIG, PHASE1_CONSTRAINTS
    
    print(f"Imaginarium Phase {PHASE} Generator")
    print(f"Spec: {SPEC_VERSION}")
    print()
    
    # Validate input
    if args.image:
        input_path = Path(args.image)
        if not input_path.exists():
            print(f"ERROR: Input image not found: {input_path}")
            return 1
        print(f"Input: {input_path}")
    else:
        print("ERROR: --image required for Phase 1")
        return 1
    
    # Setup context
    ctx = GenerationContext(run_seed=args.seed)
    print(f"Run seed: {ctx.run_seed}")
    print(f"Sobol seed: {ctx.sobol_seed}")
    print()
    
    # === STEP 1: Extract SoundSpec ===
    print("[1/8] Extracting SoundSpec from image...")
    extraction = extract_from_image(input_path)
    spec = extraction.spec
    
    print(f"  Fingerprint: {extraction.fingerprint[:50]}...")
    print(f"  Brightness:  {spec.brightness:.3f}")
    print(f"  Noisiness:   {spec.noisiness:.3f}")
    print(f"  Warmth:      {spec.warmth:.3f}")
    print(f"  Saturation:  {spec.saturation:.3f}")
    print(f"  Contrast:    {spec.contrast:.3f}")
    print(f"  Density:     {spec.density:.3f}")
    if args.verbose:
        print(f"  Debug: {extraction.debug}")
        print("  Method affinity:")
        for method_id, affinity in sorted(spec.method_affinity.items(), key=lambda x: -x[1]):
            print(f"    {method_id}: {affinity:.2f}")
    print()
    
    # List available methods
    print("Available methods:")
    for method_id in list_methods():
        print(f"  - {method_id}")
    print()
    
    # Output directory
    output_dir = Path(args.output) if args.output else Path("packs")
    print("Pack name:", args.name)
    print("Output dir:", output_dir / args.name)
    print()
    
    # === STEP 2: Generate candidates ===
    print(f"[2/8] Generating candidates (batch_size={POOL_CONFIG.batch_size})...")
    pool = generate_candidates(ctx, spec, max_batches=1)  # 1 batch = 32 candidates
    
    print(f"  Generated: {pool.total_candidates} candidates in {pool.batches_generated} batch(es)")
    print(f"  By family: {pool.by_family}")
    print(f"  By method: {pool.by_method}")
    
    if args.verbose:
        print("\n  Candidates:")
        for c in pool.candidates[:5]:
            print(f"    {c.candidate_id}")
            print(f"      seed={c.seed}, family={c.family}")
        if len(pool.candidates) > 5:
            print(f"    ... and {len(pool.candidates) - 5} more")
    print()
    
    # === STEP 3: Render previews ===
    from .render import NRTRenderer, find_sclang
    
    sclang = find_sclang()
    if sclang is None:
        print("[3/8] Render previews - SKIPPED (sclang not found)")
        print("  Install SuperCollider to enable rendering")
        print()
        print("[4-8] Remaining steps skipped (no audio)")
        return 0
    
    print(f"[3/8] Rendering previews...")
    
    # Render all candidates
    renderer = NRTRenderer(sclang_path=sclang)
    
    def render_progress(i, total, cid):
        print(f"  [{i+1}/{total}] {cid.split(':')[0]}...")
    
    render_result = renderer.render_batch(pool.candidates, progress_callback=render_progress)
    
    print(f"  Rendered: {render_result.successful}/{len(pool.candidates)}")
    print()
    
    # === STEP 4: Safety gates ===
    from .safety import check_safety
    
    print("[4/8] Running safety gates...")
    
    safe_count = 0
    for c in pool.candidates:
        if c.audio_path and c.audio_path.exists():
            c.safety = check_safety(c.audio_path)
            if c.safety.passed:
                safe_count += 1
    
    print(f"  Passed: {safe_count}/{render_result.successful}")
    print()
    
    # === STEP 5: Analyze features ===
    from .analyze import extract_features
    
    print("[5/8] Extracting features...")
    
    feature_count = 0
    for c in pool.candidates:
        if c.safety and c.safety.passed and c.audio_path:
            try:
                c.features = extract_features(c.audio_path)
                feature_count += 1
            except Exception as e:
                if args.verbose:
                    print(f"  Warning: {c.candidate_id}: {e}")
    
    print(f"  Extracted: {feature_count}/{safe_count}")
    print()
    
    # === STEP 6: Score fit ===
    from .score import score_candidates
    
    print("[6/8] Scoring fit...")
    
    candidates_with_features = [c for c in pool.candidates if c.features is not None]
    scores = score_candidates(candidates_with_features, spec)
    
    if scores:
        print(f"  Scored: {len(scores)} candidates")
        print(f"  Fit range: {min(scores):.3f} - {max(scores):.3f}")
        print(f"  Mean fit: {sum(scores)/len(scores):.3f}")
    print()
    
    # === STEP 7: Select diverse set ===
    from .select import select_diverse
    
    print("[7/8] Selecting diverse set...")
    
    # Check if spatial selection is enabled
    use_spatial = getattr(args, 'spatial', False)
    spatial_analysis = None
    
    if use_spatial:
        from .spatial import analyze_for_spatial
        from .selection import select_by_role, wrap_candidate
        from PIL import Image
        import numpy as np
        
        # Run spatial analysis
        img = np.array(Image.open(input_path).convert("RGB"))
        use_spatial_sel, slot_allocation, spatial_analysis = analyze_for_spatial(img)
        
        if use_spatial_sel:
            print(f"  Spatial analysis: {slot_allocation}")
            print(f"  Quality: {spatial_analysis.get('quality_score', 0):.3f}")
            
            # Wrap candidates for role selection
            usable = [c for c in pool.candidates if c.usable]
            wrapped = []
            for c in usable:
                from .selection import SelectionCandidate, CandidateFeatures as SelFeatures
                feat = c.features
                wrapped.append(SelectionCandidate(
                    candidate_id=c.candidate_id,
                    global_score=c.fit_score or 0.5,
                    features=SelFeatures(
                        crest=feat.crest if feat else 0.5,
                        onset_density=feat.onset_density if feat else 0.5,
                        noisiness=feat.flatness if feat else 0.5,
                        harmonicity=feat.harmonicity if feat else 0.5,
                        brightness=feat.centroid if feat else 0.5,
                    ),
                    tags=c.tags,
                    family=c.family,  # For family diversity penalty
                ))
            
            # Run role-based selection
            selected_wrapped, sel_debug = select_by_role(wrapped, slot_allocation)
            
            # Map back to original candidates
            id_to_cand = {c.candidate_id: c for c in usable}
            selected_list = [id_to_cand[w.candidate_id] for w in selected_wrapped]
            
            # Mark as selected
            for c in selected_list:
                c.selected = True
            
            # Build result object compatible with export
            from collections import Counter
            family_counts = Counter(c.family for c in selected_list)
            
            class SpatialSelectionResult:
                def __init__(self, selected, family_counts, slot_allocation):
                    self.selected = selected
                    self.family_counts = dict(family_counts)
                    self.pairwise_distances = {"min": 0, "mean": 0, "max": 0}
                    self.relaxations_applied = []
                    self.deadlock = None
                    self.slot_allocation = slot_allocation
            
            selection = SpatialSelectionResult(selected_list, family_counts, slot_allocation)
            
            print(f"  Selected: {len(selection.selected)}/8")
            print(f"  By role: {slot_allocation}")
            print(f"  Family counts: {selection.family_counts}")
        else:
            print(f"  Spatial fallback (quality={spatial_analysis.get('quality_score', 0):.3f})")
            use_spatial = False
    
    if not use_spatial:
        selection = select_diverse(pool.candidates, n_select=PHASE1_CONSTRAINTS.n_select)
        
        print(f"  Selected: {len(selection.selected)}/{PHASE1_CONSTRAINTS.n_select}")
        print(f"  Family counts: {selection.family_counts}")
        print(f"  Pairwise distances: min={selection.pairwise_distances['min']:.3f}, mean={selection.pairwise_distances['mean']:.3f}")
        
        if selection.relaxations_applied and max(selection.relaxations_applied) > 0:
            print(f"  Relaxations used: {selection.relaxations_applied}")
        
        if selection.deadlock:
            print(f"  WARNING: {selection.deadlock.constraint_failures}")
    print()
    
    # === STEP 8: Export pack ===
    from .export import export_pack
    
    print("[8/8] Exporting pack...")
    
    if not selection.selected:
        print("  ERROR: No candidates selected, cannot export")
        return 1
    
    pack_path = export_pack(
        pack_name=args.name,
        selected=selection.selected,
        spec=spec,
        context=ctx,
        input_fingerprint=extraction.fingerprint,
        output_dir=output_dir,
        all_candidates=pool.candidates,
        selection_result=selection,
    )
    
    print(f"  Pack: {pack_path}")
    print(f"  Generators: {len(selection.selected)}")
    print()
    
    # Summary
    print("=" * 50)
    print("COMPLETE")
    print(f"  Input:  {input_path}")
    print(f"  Output: {pack_path}")
    print(f"  Generators: {len(selection.selected)}")
    for i, c in enumerate(selection.selected):
        print(f"    [{i+1}] {c.method_id} (fit={c.fit_score:.3f})")
    
    return 0


def cmd_list_methods(args: argparse.Namespace) -> int:
    """List available synthesis methods."""
    from .methods import get_all_methods
    
    print("Registered synthesis methods:")
    print()
    
    methods = get_all_methods()
    if not methods:
        print("  (none)")
        return 0
    
    # Group by family
    by_family = {}
    for method_id, template in methods.items():
        family = template.definition.family
        if family not in by_family:
            by_family[family] = []
        by_family[family].append(template)
    
    for family, templates in sorted(by_family.items()):
        print(f"[{family}]")
        for t in templates:
            d = t.definition
            print(f"  {d.method_id}")
            print(f"    Display: {d.display_name}")
            print(f"    Version: {d.template_version}")
            print(f"    Params: {', '.join(p.name for p in d.param_axes)}")
            print(f"    Macros: {', '.join(m.name for m in d.macro_controls)}")
        print()
    
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify a generated pack meets contract requirements."""
    pack_path = Path(args.pack)
    
    if not pack_path.exists():
        print(f"ERROR: Pack not found: {pack_path}")
        return 1
    
    print(f"Verifying pack: {pack_path}")
    print()
    
    # TODO: Implement verification
    # - Check manifest.json
    # - Validate generator JSONs
    # - Parse SynthDef arglists
    # - Check seed arg presence
    
    print("TODO: Implement pack verification")
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    """Generate and render a single preview from a method."""
    from .methods import get_method
    from .seeds import GenerationContext
    
    method = get_method(args.method)
    if method is None:
        print(f"ERROR: Unknown method: {args.method}")
        return 1
    
    ctx = GenerationContext(run_seed=args.seed)
    
    # Sample params from macros (all at 0.5 for preview)
    macro_values = {m.name: 0.5 for m in method.definition.macro_controls}
    params = method.sample_params(macro_values)
    
    print(f"Method: {args.method}")
    print(f"Seed: {args.seed}")
    print(f"Params: {params}")
    print()
    
    # Generate SynthDef
    synthdef_name = f"imaginarium_preview_{args.seed}"
    scd = method.generate_synthdef(synthdef_name, params, args.seed)
    
    print("Generated SynthDef:")
    print("-" * 60)
    print(scd)
    print("-" * 60)
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(scd)
        print(f"Written to: {output_path}")
    
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    """Extract SoundSpec from an image (for testing/debugging)."""
    from .extract import extract_from_image
    import json
    
    input_path = Path(args.image)
    if not input_path.exists():
        print(f"ERROR: Image not found: {input_path}")
        return 1
    
    result = extract_from_image(input_path)
    
    print(f"Image: {input_path}")
    print(f"Size: {result.debug['image_size']}")
    print()
    print("SoundSpec:")
    print(f"  brightness: {result.spec.brightness:.4f}")
    print(f"  noisiness:  {result.spec.noisiness:.4f}")
    print()
    print("Debug values:")
    for key, val in result.debug.items():
        if key not in ('image_size',):
            if isinstance(val, float):
                print(f"  {key}: {val:.4f}")
            else:
                print(f"  {key}: {val}")
    print()
    print(f"Fingerprint: {result.fingerprint}")
    
    if args.json:
        output = {
            "spec": result.spec.to_dict(),
            "fingerprint": result.fingerprint,
            "debug": {k: (float(v) if isinstance(v, float) else v) for k, v in result.debug.items()},
        }
        print()
        print("JSON:")
        print(json.dumps(output, indent=2))
    
    return 0


def cmd_render_test(args: argparse.Namespace) -> int:
    """Test NRT rendering with a single candidate."""
    from .render import find_sclang, NRTRenderer
    from .generate import CandidateGenerator
    from .seeds import GenerationContext
    from .models import SoundSpec
    from pathlib import Path
    
    print("Imaginarium Render Test")
    print("=" * 40)
    
    # Check for sclang
    sclang = find_sclang()
    if sclang is None:
        print("ERROR: sclang not found")
        print()
        print("Searched locations:")
        print("  - PATH")
        print("  - /Applications/SuperCollider.app/Contents/MacOS/sclang")
        print("  - /usr/bin/sclang")
        print("  - /usr/local/bin/sclang")
        return 1
    
    print(f"sclang: {sclang}")
    print()
    
    # Generate a single test candidate
    ctx = GenerationContext(run_seed=args.seed)
    spec = SoundSpec(brightness=0.5, noisiness=0.5)
    
    generator = CandidateGenerator(ctx, spec)
    batch = generator.generate_batch(0)
    
    if not batch.candidates:
        print("ERROR: No candidates generated")
        return 1
    
    candidate = batch.candidates[0]
    print(f"Test candidate: {candidate.candidate_id}")
    print(f"  seed: {candidate.seed}")
    print(f"  params: {candidate.params}")
    print()
    
    # Render
    output_dir = Path(args.output) if args.output else None
    renderer = NRTRenderer(sclang_path=sclang, output_dir=output_dir)
    
    print("Rendering...")
    result = renderer.render_candidate(candidate)
    
    if result.success:
        print(f"SUCCESS: {result.audio_path}")
        print(f"  Duration: {result.duration_sec}s")
        if result.audio_path:
            print(f"  Size: {result.audio_path.stat().st_size} bytes")
    else:
        print(f"FAILED: {result.error}")
        return 1
    
    return 0


def cmd_spatial_preview(args: argparse.Namespace) -> int:
    """Preview spatial analysis on an image."""
    import json
    from .spatial import preview_spatial_analysis
    
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"ERROR: Image not found: {image_path}")
        return 1
    
    result = preview_spatial_analysis(image_path)
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return 1
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Spatial Analysis: {image_path.name}")
        print("=" * 50)
        print(f"Use spatial: {result.get('use_spatial', False)}")
        print(f"Quality score: {result.get('quality_score', 0):.3f}")
        print()
        
        slot_alloc = result.get('slot_allocation', {})
        print("Slot allocation:")
        for role in ['accent', 'foreground', 'motion', 'bed']:
            count = slot_alloc.get(role, 0)
            print(f"  {role:12s}: {count} generators")
        print()
        
        grid = result.get('role_grid', [])
        if grid:
            print("Role grid (4x4):")
            for row in grid:
                print("  " + " ".join(row))
        print()
        
        checks = result.get('quality_checks', {})
        if checks:
            print("Quality checks:")
            for check, passed in checks.items():
                status = "✓" if passed else "✗"
                print(f"  {status} {check}")
    
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="imaginarium",
        description=f"Imaginarium sound palette generator (Phase {PHASE})",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__} (spec {SPEC_VERSION})"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate a pack from input")
    gen_parser.add_argument("--image", "-i", type=str, help="Input image path")
    gen_parser.add_argument("--name", "-n", type=str, required=True, help="Pack name")
    gen_parser.add_argument("--seed", "-s", type=int, default=42, help="Run seed")
    gen_parser.add_argument("--output", "-o", type=str, help="Output directory")
    gen_parser.add_argument("--verbose", "-v", action="store_true", help="Show debug info")
    gen_parser.add_argument("--spatial", action="store_true", help="Use spatial role-based selection")
    gen_parser.set_defaults(func=cmd_generate)
    
    # list-methods command
    list_parser = subparsers.add_parser("list-methods", help="List synthesis methods")
    list_parser.set_defaults(func=cmd_list_methods)
    
    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a pack")
    verify_parser.add_argument("--pack", "-p", type=str, required=True, help="Pack path")
    verify_parser.set_defaults(func=cmd_verify)
    
    # preview command
    preview_parser = subparsers.add_parser("preview", help="Preview a single method")
    preview_parser.add_argument("--method", "-m", type=str, required=True, help="Method ID")
    preview_parser.add_argument("--seed", "-s", type=int, default=42, help="Seed value")
    preview_parser.add_argument("--output", "-o", type=str, help="Output .scd file")
    preview_parser.set_defaults(func=cmd_preview)
    
    # extract command
    extract_parser = subparsers.add_parser("extract", help="Extract SoundSpec from image")
    extract_parser.add_argument("--image", "-i", type=str, required=True, help="Input image")
    extract_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    extract_parser.set_defaults(func=cmd_extract)
    
    # render-test command
    render_parser = subparsers.add_parser("render-test", help="Test NRT rendering")
    render_parser.add_argument("--seed", "-s", type=int, default=42, help="Test seed")
    render_parser.add_argument("--output", "-o", type=str, help="Output directory")
    render_parser.set_defaults(func=cmd_render_test)
    
    # Spatial preview command
    spatial_parser = subparsers.add_parser("spatial-preview", help="Preview spatial analysis on image")
    spatial_parser.add_argument("--image", "-i", type=str, required=True, help="Input image")
    spatial_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    spatial_parser.set_defaults(func=cmd_spatial_preview)
    
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
