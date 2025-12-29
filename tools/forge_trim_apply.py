#!/usr/bin/env python3
"""
Apply output_trim_db recommendations from forge_audio_validate.py to generator JSON files.

Default behavior:
- run validator (render + verbose)
- parse "Trim recommendations" lines: "<gen_id>: +X.Y dB"
- SET generator JSON output_trim_db to that value (absolute), clamped to range

Supports --runs N to reduce stochastic "hunting" by aggregating multiple renders.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

RE_TRIM_LINE = re.compile(r"^\s*([a-z0-9_]+):\s*([+-]?\d+(?:\.\d+)?)\s*dB\s*$", re.I)

def run_validator(pack_dir: Path, extra_args: List[str]) -> str:
    cmd = [sys.executable, "tools/forge_audio_validate.py", str(pack_dir), "--render", "-v", *extra_args]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + ("\n" + (p.stderr or "") if p.stderr else "")
    # even on PASS, returncode might be 0; on fail it might be nonzero, but we still want output
    return out

def parse_trim_recs(output: str) -> Dict[str, float]:
    lines = output.splitlines()
    try:
        idx = next(i for i, ln in enumerate(lines) if "Trim recommendations" in ln)
    except StopIteration:
        return {}

    recs: Dict[str, float] = {}
    for ln in lines[idx + 1:]:
        m = RE_TRIM_LINE.match(ln)
        if not m:
            # stop when we hit an empty line or next section
            if ln.strip() == "" or "All" in ln or "PASS" in ln:
                break
            continue
        gen_id = m.group(1)
        val = float(m.group(2))
        recs[gen_id] = val
    return recs

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pack_id", help="pack_id folder under packs/")
    ap.add_argument("--packs-root", default="packs", help="packs root (default: packs)")
    ap.add_argument("--runs", type=int, default=1, help="number of renders to aggregate (default: 1)")
    ap.add_argument("--agg", choices=["median", "mean"], default="median", help="aggregation (default: median)")
    ap.add_argument("--clamp-lo", type=float, default=-24.0, help="min output_trim_db (default: -24)")
    ap.add_argument("--clamp-hi", type=float, default=24.0, help="max output_trim_db (default: +24)")
    ap.add_argument("--dry-run", action="store_true", help="print changes, don’t write")
    ap.add_argument("--extra", nargs="*", default=[], help="extra args passed to forge_audio_validate.py")
    args = ap.parse_args()

    pack_dir = Path(args.packs_root) / args.pack_id
    gen_dir = pack_dir / "generators"
    if not gen_dir.exists():
        print(f"ERROR: {gen_dir} not found", file=sys.stderr)
        return 2

    all_runs: List[Dict[str, float]] = []
    for n in range(args.runs):
        out = run_validator(pack_dir, args.extra)
        recs = parse_trim_recs(out)
        if not recs:
            print("ERROR: no trim recommendations found in validator output", file=sys.stderr)
            # print tail for debugging
            print(out[-2000:], file=sys.stderr)
            return 3
        all_runs.append(recs)

    # build per-gen list
    by_gen: Dict[str, List[float]] = {}
    for recs in all_runs:
        for gen_id, val in recs.items():
            by_gen.setdefault(gen_id, []).append(val)

    # aggregate
    agg_vals: Dict[str, float] = {}
    for gen_id, vals in by_gen.items():
        if args.agg == "mean":
            agg = statistics.fmean(vals)
        else:
            agg = statistics.median(vals)
        agg_vals[gen_id] = clamp(agg, args.clamp_lo, args.clamp_hi)

    # apply
    changes: List[Tuple[str, float, float, str]] = []
    for gen_id, new_val in sorted(agg_vals.items()):
        json_path = gen_dir / f"{gen_id}.json"
        if not json_path.exists():
            continue
        data = load_json(json_path)
        old_val = float(data.get("output_trim_db", 0.0))
        if abs(old_val - new_val) < 0.05:
            continue
        data["output_trim_db"] = round(new_val, 2)
        if not args.dry_run:
            save_json(json_path, data)
        changes.append((gen_id, old_val, new_val, str(json_path)))

    if not changes:
        print("No output_trim_db changes needed.")
        return 0

    for gen_id, old_v, new_v, path in changes:
        print(f"{gen_id}: {old_v:+.2f} dB -> {new_v:+.2f} dB  ({path})")

    if args.runs > 1:
        print(f"\nNote: aggregated over {args.runs} runs using {args.agg} (helps stochastic hunting).")

    if args.dry_run:
        print("\n(dry-run: no files written)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
