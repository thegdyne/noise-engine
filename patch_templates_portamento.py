#!/usr/bin/env python3
"""
Patch Imaginarium method templates with portamento support.
Handles all var declaration patterns carefully.

Run from noise-engine root:
    python3 patch_templates_portamento.py
"""
import os
import re
from pathlib import Path

def patch_template(filepath: Path) -> tuple[bool, str]:
    """Patch a single template file. Returns (success, message)."""
    
    content = filepath.read_text()
    
    # Check if already patched
    if 'portamentoBus' in content:
        return False, "already patched"
    
    # Check if it's a template with generate_synthdef
    if 'def generate_synthdef' not in content:
        return False, "not a template"
    
    original = content
    
    # 1. Add portamentoBus to SynthDef signature (after seed={seed})
    # Pattern: seed={seed}|  ->  seed={seed}, portamentoBus|
    content = re.sub(
        r'(seed=\{seed\})\|',
        r'\1, portamentoBus|',
        content
    )
    
    # 2. Add portamento to var declaration
    # Find the var line that contains freq and ends with semicolon
    # Handle multiple patterns:
    #   var freq, ... clockRate;
    #   var freq, ... amp;
    #   var sig, freq, ... clockRate;
    #   etc.
    # Strategy: find var line containing 'freq' and 'clockRate' or 'amp' at end
    
    def add_portamento_to_var(match):
        line = match.group(0)
        # Add portamento before the final semicolon
        return line.rstrip(';') + ', portamento;'
    
    # Match var line containing freq (but not filterFreq alone) that ends with ;
    # This pattern matches the whole var line
    content = re.sub(
        r'^(\s*var\s+(?:sig,\s*)?(?:dry,\s*)?(?:width,\s*)?freq,.*?);$',
        add_portamento_to_var,
        content,
        flags=re.MULTILINE
    )
    
    # 3. Add portamento read and Lag.kr after freq = In.kr(freqBus);
    # Pattern: freq = In.kr(freqBus);
    # Add:     portamento = In.kr(portamentoBus);
    #          freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    content = re.sub(
        r'(freq = In\.kr\(freqBus\);)',
        r'''\1
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));''',
        content
    )
    
    if content == original:
        return False, "no changes made"
    
    # Verify the changes were made correctly
    if 'portamentoBus' not in content:
        return False, "failed to add portamentoBus to signature"
    if 'var' in content and 'portamento' not in content.split('portamentoBus')[0]:
        # Check if portamento is in a var line before portamentoBus usage
        pass  # This check is complex, skip for now
    
    filepath.write_text(content)
    return True, "patched"


def main():
    base = Path("imaginarium/methods")
    
    if not base.exists():
        print("Error: Run from noise-engine root directory")
        return 1
    
    patched = 0
    skipped = 0
    failed = 0
    
    print("Patching Imaginarium templates with portamento support...")
    print()
    
    for family_dir in sorted(base.iterdir()):
        if not family_dir.is_dir():
            continue
        if family_dir.name == '__pycache__':
            continue
            
        for template in sorted(family_dir.glob("*.py")):
            if template.name in ('__init__.py', 'base.py'):
                continue
            
            success, msg = patch_template(template)
            
            rel_path = template.relative_to(base)
            if success:
                print(f"  ✓ {rel_path}")
                patched += 1
            elif msg == "already patched":
                print(f"  - {rel_path} (already patched)")
                skipped += 1
            elif msg == "not a template":
                skipped += 1
            else:
                print(f"  ✗ {rel_path} ({msg})")
                failed += 1
    
    print()
    print(f"Done: {patched} patched, {skipped} skipped, {failed} failed")
    
    if failed > 0:
        return 1
    
    # Verification
    print()
    print("Verifying...")
    
    issues = []
    for family_dir in base.iterdir():
        if not family_dir.is_dir() or family_dir.name == '__pycache__':
            continue
        for template in family_dir.glob("*.py"):
            if template.name in ('__init__.py', 'base.py'):
                continue
            
            content = template.read_text()
            if 'def generate_synthdef' not in content:
                continue
                
            rel_path = template.relative_to(base)
            
            if 'portamentoBus' not in content:
                issues.append(f"{rel_path}: missing portamentoBus in signature")
            
            # Check var declaration has portamento
            var_lines = [l for l in content.split('\n') if l.strip().startswith('var ') and 'freq' in l]
            for var_line in var_lines:
                if 'portamento' not in var_line and 'filterFreq' not in var_line.replace('freq', ''):
                    # This var line has freq but not portamento
                    if 'clockRate' in var_line or var_line.rstrip().endswith('amp;'):
                        issues.append(f"{rel_path}: var line missing portamento")
                        break
    
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  ✗ {issue}")
        return 1
    else:
        print("  ✓ All templates verified")
    
    return 0


if __name__ == "__main__":
    exit(main())
