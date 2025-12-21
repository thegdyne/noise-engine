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
    from .methods import list_methods, get_all_methods
    
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
    if args.verbose:
        print(f"  Debug: {extraction.debug}")
    print()
    
    # List available methods
    print("Available methods:")
    for method_id in list_methods():
        print(f"  - {method_id}")
    print()
    
    # TODO: Phase 1 implementation
    # 2. Generate candidates
    # 3. Render previews (NRT)
    # 4. Run safety gates
    # 5. Analyze features
    # 6. Score fit
    # 7. Select diverse set
    # 8. Export pack
    
    print("Pack name:", args.name)
    print("Output dir:", args.output or f"packs/{args.name}")
    print()
    print("[2/8] Generate candidates - TODO")
    print("[3/8] Render previews (NRT) - TODO")
    print("[4/8] Run safety gates - TODO")
    print("[5/8] Analyze features - TODO")
    print("[6/8] Score fit - TODO")
    print("[7/8] Select diverse set - TODO")
    print("[8/8] Export pack - TODO")
    
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
    
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
