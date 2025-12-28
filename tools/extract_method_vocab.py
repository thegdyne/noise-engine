#!/usr/bin/env python3
"""
tools/extract_method_vocab.py
Extract synthesis method metadata from imaginarium/methods/ to generate
synthesis_methods.yaml vocabulary file.

Usage:
    python tools/extract_method_vocab.py
    python tools/extract_method_vocab.py --output reference/synthesis_methods.yaml
"""

import argparse
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Any

import yaml


def discover_method_classes(methods_dir: Path) -> Dict[str, List[str]]:
    """
    Discover all method template classes organized by family.
    
    Returns:
        Dict of family -> list of module names
    """
    families = {}
    
    for family_dir in methods_dir.iterdir():
        if not family_dir.is_dir():
            continue
        if family_dir.name.startswith('_'):
            continue
            
        family_name = family_dir.name
        methods = []
        
        for py_file in family_dir.glob('*.py'):
            if py_file.name.startswith('_'):
                continue
            methods.append(py_file.stem)
        
        if methods:
            families[family_name] = sorted(methods)
    
    return families


def load_method_template(family: str, method: str):
    """
    Dynamically load a method template class.
    
    Returns:
        Instance of MethodTemplate or None
    """
    try:
        module_path = f"imaginarium.methods.{family}.{method}"
        module = importlib.import_module(module_path)
        
        # Find the template class (ends with 'Template')
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name.endswith('Template'):
                # Skip the base class
                if name == 'MethodTemplate':
                    continue
                return obj()
        
        return None
    except Exception as e:
        print(f"Warning: Could not load {family}/{method}: {e}", file=sys.stderr)
        return None


def extract_method_metadata(template) -> Dict[str, Any]:
    """
    Extract metadata from a method template instance.
    """
    d = template.definition
    
    # Get sample tags
    sample_params = {a.name: a.default for a in d.param_axes}
    tags = template.get_tags(sample_params)
    
    return {
        "id": d.method_id,
        "display_name": d.display_name,
        "template_version": d.template_version,
        "param_count": len(d.param_axes),
        "params": [
            {
                "name": a.name,
                "label": a.label,
                "tooltip": a.tooltip,
                "range": [a.min_val, a.max_val],
                "curve": a.curve,
            }
            for a in d.param_axes[:5]  # Max 5 exposed
        ],
        "macro_controls": [m.name for m in d.macro_controls],
        "default_tags": d.default_tags,
        "sample_tags": tags,
    }


def build_vocabulary(methods_dir: Path) -> Dict[str, Any]:
    """
    Build the complete vocabulary structure.
    """
    families_discovered = discover_method_classes(methods_dir)
    
    vocab = {
        "schema_version": "1.0",
        "generated_from": str(methods_dir),
        "families": {},
        "diversity": {
            "min_families": 3,
            "max_per_family": 4,
            "recommended_families": 4,
        },
    }
    
    for family_name, method_names in sorted(families_discovered.items()):
        family_data = {
            "description": "",  # Would need docstring extraction
            "methods": {},
        }
        
        for method_name in method_names:
            template = load_method_template(family_name, method_name)
            if template:
                metadata = extract_method_metadata(template)
                family_data["methods"][method_name] = metadata
            else:
                # Placeholder for methods that couldn't be loaded
                family_data["methods"][method_name] = {
                    "id": f"{family_name}/{method_name}",
                    "display_name": method_name.replace('_', ' ').title(),
                    "error": "Could not load template",
                }
        
        vocab["families"][family_name] = family_data
    
    return vocab


def generate_markdown_table(vocab: Dict[str, Any]) -> str:
    """
    Generate markdown table for GENERATOR_PACK_SESSION.md.
    """
    lines = [
        "| Family | Method ID | Display Name | Params |",
        "|--------|-----------|--------------|--------|",
    ]
    
    for family_name, family_data in sorted(vocab["families"].items()):
        for method_name, method_data in sorted(family_data["methods"].items()):
            method_id = method_data.get("id", f"{family_name}/{method_name}")
            display = method_data.get("display_name", method_name)
            param_count = method_data.get("param_count", "?")
            lines.append(f"| {family_name} | `{method_id}` | {display} | {param_count} |")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract method vocabulary from imaginarium/methods/"
    )
    parser.add_argument(
        "--methods-dir",
        type=Path,
        default=Path("imaginarium/methods"),
        help="Path to methods directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reference/synthesis_methods.yaml"),
        help="Output YAML file"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Also print markdown table"
    )
    
    args = parser.parse_args()
    
    if not args.methods_dir.exists():
        print(f"Error: Methods directory not found: {args.methods_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Add parent to path for imports
    sys.path.insert(0, str(args.methods_dir.parent.parent))
    
    print(f"Scanning {args.methods_dir}...")
    vocab = build_vocabulary(args.methods_dir)
    
    # Count results
    total_methods = sum(
        len(f["methods"]) for f in vocab["families"].values()
    )
    print(f"Found {len(vocab['families'])} families, {total_methods} methods")
    
    # Write YAML
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        yaml.dump(vocab, f, default_flow_style=False, sort_keys=False)
    print(f"Wrote {args.output}")
    
    # Optional markdown
    if args.markdown:
        print("\n--- Markdown Table ---\n")
        print(generate_markdown_table(vocab))


if __name__ == "__main__":
    main()
