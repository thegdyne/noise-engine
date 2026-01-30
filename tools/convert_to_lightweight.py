#!/usr/bin/env python3
"""Convert monolithic SuperCollider generator SynthDefs to lightweight end-stage format.

Usage:
    python tools/convert_to_lightweight.py packs/duga          # dry-run one pack
    python tools/convert_to_lightweight.py all                  # dry-run all packs
    python tools/convert_to_lightweight.py packs/duga --apply   # write changes
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Variables to strip from var declarations
# ---------------------------------------------------------------------------
STRIP_VARS = {
    'filterFreq', 'rq', 'filterType', 'attack', 'decay',
    'amp', 'ampVal', 'envSource', 'clockRate', 'portamento',
}


def detect_pack_name(filepath: Path) -> str:
    """Extract pack name from file path like packs/duga/generators/signal.scd -> duga."""
    parts = filepath.parts
    for i, p in enumerate(parts):
        if p == 'packs' and i + 1 < len(parts):
            return parts[i + 1]
    return 'unknown'


def detect_gen_name(filepath: Path) -> str:
    """Extract generator name from filename (without extension)."""
    return filepath.stem


def count_custom_params_from_json(scd_path: Path) -> int:
    """Try to read the companion .json to find how many custom params exist."""
    json_path = scd_path.with_suffix('.json')
    if json_path.exists():
        try:
            with open(json_path) as f:
                data = json.load(f)
            return len(data.get('custom_params', []))
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def is_already_converted(content: str) -> bool:
    """Check if file is already converted (has ReplaceOut)."""
    return 'ReplaceOut.ar' in content


def _is_line_removable_busread(line: str) -> bool:
    """Check if a line is a standard bus read that should be removed."""
    s = line.strip()
    # filterFreq = In.kr(cutoffBus)...
    if re.match(r'filterFreq\s*=\s*In\.kr\(cutoffBus\)', s):
        return True
    # rq = In.kr(resBus)...
    if re.match(r'rq\s*=\s*In\.kr\(resBus\)', s):
        return True
    # attack = In.kr(attackBus)...
    if re.match(r'attack\s*=\s*In\.kr\(attackBus\)', s):
        return True
    # decay = In.kr(decayBus)...
    if re.match(r'decay\s*=\s*In\.kr\(decayBus\)', s):
        return True
    # filterType = In.kr(filterTypeBus)...
    if re.match(r'filterType\s*=\s*In\.kr\(filterTypeBus\)', s):
        return True
    # envSource = In.kr(envSourceBus)...
    if re.match(r'envSource\s*=\s*In\.kr\(envSourceBus\)', s):
        return True
    # clockRate = In.kr(clockRateBus)...
    if re.match(r'clockRate\s*=\s*In\.kr\(clockRateBus\)', s):
        return True
    # amp/ampVal = In.kr(~params[\amplitude])...
    if re.match(r'(?:amp|ampVal)\s*=\s*In\.kr\(~params\[\\amplitude\]\)', s):
        return True
    # portamento = In.kr(portamentoBus)...
    if re.match(r'portamento\s*=\s*In\.kr\(portamentoBus\)', s):
        return True
    return False


def _is_portamento_lag(line: str) -> bool:
    """Check if line is: freq = Lag.kr(freq, portamento...)."""
    return bool(re.match(r'\s*freq\s*=\s*Lag\.kr\(freq,\s*portamento', line))


def _is_output_chain_line(line: str) -> bool:
    """Check if a line is part of the output chain to remove."""
    s = line.strip()
    patterns = [
        r'sig\s*=\s*LeakDC\.ar\(sig\)',
        r'sig\s*=\s*~multiFilter\.\(sig',
        r'sig\s*=\s*~envVCA\.\(sig',
        r'sig\s*=\s*Limiter\.ar\(sig',
        r'sig\s*=\s*~ensure2ch\.\(sig\)',
        r'Out\.ar\(out,\s*sig\)',
    ]
    for pat in patterns:
        if re.match(pat, s):
            return True
    return False


def _is_output_chain_comment(line: str) -> bool:
    """Check if a line is a comment about the output chain."""
    s = line.strip()
    if re.match(r'//\s*Output chain', s):
        return True
    if re.match(r'//\s*===\s*PROCESSING CHAIN\s*===', s):
        return True
    return False


def _is_custom_bus_read(line: str):
    """Check if line reads a custom bus. Returns match or None.
    Matches: varname = In.kr(customBusN)... ;
    """
    m = re.match(
        r'^(\s*)(\w+)\s*=\s*In\.kr\(customBus(\d)\)(.*?);(.*)$',
        line
    )
    return m


def _is_freq_read(line: str) -> bool:
    """Check if line is: freq = In.kr(freqBus);"""
    return bool(re.match(r'\s*freq\s*=\s*In\.kr\(freqBus\)\s*;', line))


def _is_section_comment(line: str) -> bool:
    """Check if a line is a section comment like '// Standard reads' or '// Theme params' or '// Custom params'."""
    s = line.strip()
    if re.match(r'//\s*(Standard reads|Standard params|Theme params|Custom params)\s*$', s):
        return True
    return False


def convert_content(content: str, pack_name: str, gen_name: str, num_params: int) -> str:
    """Apply all transforms to file content. Returns converted content."""
    lines = content.split('\n')

    # Phase 1: Gather info about custom bus reads
    custom_reads = {}  # bus_idx -> (line_idx, var_name, chain_suffix, comment, indent)
    for i, line in enumerate(lines):
        m = _is_custom_bus_read(line)
        if m:
            indent = m.group(1)
            var_name = m.group(2)
            bus_idx = int(m.group(3))
            chain = m.group(4)  # e.g. .linlin(0, 1, 0.3, 1)
            comment = m.group(5).strip()
            custom_reads[bus_idx] = (i, var_name, chain, comment, indent)

    if num_params is None:
        if custom_reads:
            num_params = max(custom_reads.keys()) + 1
        else:
            num_params = 5

    # Phase 2: Process line by line
    result_lines = []
    i = 0
    arg_block_done = False
    first_var_seen = False
    p_line_inserted = False
    in_arg_block = False
    arg_block_lines = []
    freq_read_inserted = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- Transform 1: Arg block ---
        # Detect start of arg block: SynthDef(..., { |
        if not arg_block_done and ('{' in stripped and '|' in stripped):
            # Collect all lines of the arg block until we find the closing |
            arg_block_lines.append(line)
            in_arg_block = True
            # Check if closing | is on the same line (after the opening |)
            # Find the arg content between { | and |
            combined = line
            while True:
                # Count pipe chars
                pipe_count = combined.count('|')
                if pipe_count >= 2:
                    break
                i += 1
                if i >= len(lines):
                    break
                arg_block_lines.append(lines[i])
                combined += '\n' + lines[i]

            # Now reconstruct the arg block
            # Extract the SynthDef prefix (everything before {)
            full_text = '\n'.join(arg_block_lines)

            # Check if this has monolithic args
            if 'cutoffBus' in full_text:
                # Find prefix before { |
                prefix_match = re.search(r'^(.*?\{\s*)\|', full_text, re.DOTALL)
                if prefix_match:
                    prefix = prefix_match.group(1)
                    result_lines.append(f'{prefix}|out, freqBus, customBus0|')
                else:
                    # Fallback: just output as-is
                    for al in arg_block_lines:
                        result_lines.append(al)
            else:
                # Not monolithic, keep as-is
                for al in arg_block_lines:
                    result_lines.append(al)

            arg_block_done = True
            i += 1
            continue

        # --- Transform 2: Variable declaration cleanup ---
        if arg_block_done and stripped.startswith('var ') and stripped.endswith(';') and not stripped.startswith('var p '):
            var_body = stripped[4:-1]  # remove 'var ' and ';'
            declared = [v.strip() for v in var_body.split(',')]

            has_strip = any(v in STRIP_VARS for v in declared)
            if has_strip:
                remaining = [v for v in declared if v not in STRIP_VARS]
                if remaining:
                    indent = line[:len(line) - len(line.lstrip())]
                    result_lines.append(f'{indent}var {", ".join(remaining)};')
                    if not first_var_seen:
                        first_var_seen = True
                        # Insert var p line right after this first var declaration
                        if custom_reads and not p_line_inserted:
                            result_lines.append(f'{indent}var p = In.kr(customBus0, {num_params});')
                            p_line_inserted = True
                # If remaining is empty, drop the line entirely
                # But still track first_var for p insertion
                elif not first_var_seen:
                    first_var_seen = True
                    indent = line[:len(line) - len(line.lstrip())]
                    if custom_reads and not p_line_inserted:
                        result_lines.append(f'{indent}var p = In.kr(customBus0, {num_params});')
                        p_line_inserted = True
                i += 1
                continue
            else:
                # No strip vars - this is a DSP-specific var declaration, keep it
                if not first_var_seen:
                    first_var_seen = True
                    indent = line[:len(line) - len(line.lstrip())]
                    if custom_reads and not p_line_inserted:
                        result_lines.append(f'{indent}var p = In.kr(customBus0, {num_params});')
                        p_line_inserted = True
                result_lines.append(line)
                i += 1
                continue

        # --- Transform 3: Custom bus reads -> p[N] references ---
        m = _is_custom_bus_read(line)
        if m:
            indent_str = m.group(1)
            var_name = m.group(2)
            bus_idx = int(m.group(3))
            chain = m.group(4)
            comment = m.group(5).strip()

            new_line = f'{indent_str}{var_name} = p[{bus_idx}]{chain};'
            if comment:
                new_line += f'  {comment}'
            result_lines.append(new_line)
            i += 1
            continue

        # --- Remove standard bus reads ---
        if _is_line_removable_busread(line):
            i += 1
            continue

        # --- Remove portamento lag, replace freq read ---
        if _is_portamento_lag(line):
            i += 1
            continue

        # Keep freq = In.kr(freqBus); as-is
        if _is_freq_read(line):
            result_lines.append(line)
            freq_read_inserted = True
            i += 1
            continue

        # --- Transform 4: Remove output chain ---
        if _is_output_chain_line(line):
            i += 1
            continue

        if _is_output_chain_comment(line):
            i += 1
            continue

        # Remove orphaned section comments (Standard reads, Theme params, Custom params)
        if _is_section_comment(line):
            i += 1
            continue

        # --- Transform 5: Mandatory tail ---
        if stripped == '}).add;':
            indent = line[:len(line) - len(line.lstrip())] or ''
            body_indent = indent + '    ' if not indent else '    '
            result_lines.append(f'{body_indent}// Mandatory tail')
            result_lines.append(f'{body_indent}sig = NumChannels.ar(sig, 2);')
            result_lines.append(f'{body_indent}ReplaceOut.ar(out, sig);')
            result_lines.append(line)
            i += 1
            continue

        # Default: keep the line
        result_lines.append(line)
        i += 1

    # Join and add header
    content = '\n'.join(result_lines)

    # Clean up excessive blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Strip trailing whitespace per line
    lines = content.split('\n')
    lines = [l.rstrip() for l in lines]
    content = '\n'.join(lines)

    # Transform 6: Header comment
    header = f'// {pack_name}/{gen_name} — Lightweight end-stage generator'
    first_line = content.split('\n')[0] if content else ''
    if 'Lightweight end-stage generator' not in first_line:
        content = header + '\n' + content

    # Ensure file ends with newline
    if not content.endswith('\n'):
        content += '\n'

    return content


def convert_file(filepath: Path, apply: bool = False) -> dict:
    """Convert a single .scd file. Returns status dict."""
    pack_name = detect_pack_name(filepath)
    gen_name = detect_gen_name(filepath)

    with open(filepath) as f:
        original = f.read()

    # Skip already-converted files
    if is_already_converted(original):
        return {'status': 'skipped', 'file': str(filepath), 'reason': 'already converted (has ReplaceOut)'}

    # Skip files without monolithic arg block
    if 'cutoffBus' not in original:
        return {'status': 'skipped', 'file': str(filepath), 'reason': 'no monolithic arg block found'}

    original_line_count = len(original.strip().split('\n'))

    # Determine number of custom params from JSON
    num_params = count_custom_params_from_json(filepath)
    if num_params is None:
        # Count from source
        indices = set()
        for m in re.finditer(r'In\.kr\(customBus(\d)\)', original):
            indices.add(int(m.group(1)))
        num_params = len(indices) if indices else None
    if num_params == 0:
        num_params = 5  # fallback

    content = convert_content(original, pack_name, gen_name, num_params)

    new_line_count = len(content.strip().split('\n'))
    reduction = ((original_line_count - new_line_count) / original_line_count * 100) if original_line_count > 0 else 0

    result = {
        'file': str(filepath),
        'original_lines': original_line_count,
        'new_lines': new_line_count,
        'reduction_pct': round(reduction, 1),
    }

    # Flag for manual review if reduction is less than 40% (may indicate parse issues)
    if reduction < 40:
        result['status'] = 'flagged'
        result['reason'] = f'only {reduction:.1f}% line reduction (< 40%)'
    else:
        result['status'] = 'changed'

    if apply:
        # Create backup
        backup_path = filepath.with_suffix('.scd.bak')
        shutil.copy2(filepath, backup_path)
        # Write converted content
        with open(filepath, 'w') as f:
            f.write(content)
        result['backup'] = str(backup_path)

    return result


def find_scd_files(pack_path: Path) -> list:
    """Find all .scd files in generators/ subdir of a pack."""
    gen_dir = pack_path / 'generators'
    if not gen_dir.exists():
        return []
    return sorted(gen_dir.glob('*.scd'))


def main():
    parser = argparse.ArgumentParser(
        description='Convert monolithic SuperCollider generators to lightweight end-stage format.'
    )
    parser.add_argument(
        'target',
        help='Pack directory path (e.g. packs/duga) or "all" for all packs'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        default=False,
        help='Actually write changes (default: dry-run)'
    )
    args = parser.parse_args()

    # Resolve paths relative to project root
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    packs_dir = project_root / 'packs'

    if args.target == 'all':
        pack_dirs = sorted([
            d for d in packs_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ])
    else:
        target = Path(args.target)
        if not target.is_absolute():
            target = project_root / target
        if not target.exists():
            print(f"Error: {target} does not exist", file=sys.stderr)
            sys.exit(1)
        pack_dirs = [target]

    changed = []
    flagged = []
    skipped = []

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'[{mode}] Converting generators to lightweight format...', file=sys.stderr)
    print(f'Scanning {len(pack_dirs)} pack(s)...', file=sys.stderr)

    for pack_dir in pack_dirs:
        scd_files = find_scd_files(pack_dir)
        if not scd_files:
            continue

        for scd_file in scd_files:
            try:
                result = convert_file(scd_file, apply=args.apply)
            except Exception as e:
                result = {
                    'status': 'flagged',
                    'file': str(scd_file),
                    'reason': f'parse error: {e}',
                }

            status = result['status']
            if status == 'changed':
                changed.append(result)
                icon = 'W' if args.apply else '~'
                print(f'  [{icon}] {result["file"]} ({result.get("reduction_pct", "?")}% reduction)', file=sys.stderr)
            elif status == 'flagged':
                flagged.append(result)
                print(f'  [!] {result["file"]} — {result.get("reason", "unknown")}', file=sys.stderr)
            elif status == 'skipped':
                skipped.append(result)
                print(f'  [-] {result["file"]} — {result.get("reason", "skipped")}', file=sys.stderr)

    # Summary
    print(f'\nSummary: {len(changed)} changed, {len(flagged)} flagged, {len(skipped)} skipped', file=sys.stderr)

    # JSON report to stdout
    report = {
        'changed': changed,
        'flagged': flagged,
        'skipped': skipped,
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
