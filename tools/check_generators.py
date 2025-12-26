#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess, run
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional, Tuple


SUMMARY_RE = re.compile(r"(issues found|All.*passed)", re.IGNORECASE)

# Broad "interesting" lines for quick diagnosis (tune as you like)
FAIL_SNIPPET_RE = re.compile(
    r"(✗|fail|failed|error|traceback|exception|nan|inf|clip|clipp|dc|silence|silent|timeout|sclang)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Target:
    kind: str  # "pack" or "gen"
    ref: str   # "pack_id" or "pack_id/gen_id"


@dataclass
class Result:
    target: Target
    rc: int
    log_path: Path
    summary: str
    fail_snippet: str


def repo_root() -> Path:
    # assume run from repo root or below it
    p = Path.cwd()
    for _ in range(5):
        if (p / "packs").is_dir() and (p / "tools").is_dir():
            return p
        p = p.parent
    return Path.cwd()


def discover_packs(packs_dir: Path) -> List[str]:
    # packs/<pack_id>/... (skip hidden)
    packs = []
    for child in packs_dir.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            packs.append(child.name)
    return sorted(packs)


def parse_targets(args: argparse.Namespace, packs_dir: Path) -> List[Target]:
    targets: List[Target] = []

    if args.targets:
        # allow mix: "pack" OR "pack/gen"
        for t in args.targets:
            if "/" in t:
                targets.append(Target("gen", t))
            else:
                targets.append(Target("pack", t))
        return targets

    # no explicit targets => default to all packs
    for p in discover_packs(packs_dir):
        targets.append(Target("pack", p))
    return targets


def safe_name(ref: str) -> str:
    return ref.replace("/", "__")


def run_validate_one(
    root: Path,
    t: Target,
    log_dir: Path,
    render: bool,
    env_mode: str,
    extra_args: List[str],
    show_fails: bool,
) -> Result:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{safe_name(t.ref)}.log"

    validate_py = root / "tools" / "forge_audio_validate.py"
    if not validate_py.exists():
        return Result(t, 2, log_path, "ERROR: missing tools/forge_audio_validate.py", "")

    # build command
    cmd = [sys.executable, str(validate_py)]
    if t.kind == "pack":
        cmd += [str(root / "packs" / t.ref)]
    else:
        # generator: expect packs/<pack>/generators/<gen>.scd exists, but validator might accept pack path only.
        # We pass the pack path and rely on extra args to allow per-gen selection if your validator supports it.
        # If your validator DOES support selecting a generator, set it up via extra_args like:
        #   --only "gen_id"
        pack = t.ref.split("/", 1)[0]
        gen = t.ref.split("/", 1)[1]
        cmd += [str(root / "packs" / pack)]
        extra_args = extra_args + ["--only", gen]

    if render:
        cmd.append("--render")
    if env_mode:
        cmd += ["--env-mode", env_mode]
    cmd += extra_args

    # run
    try:
        proc: CompletedProcess = run(
            cmd,
            stdout=log_path.open("w"),
            stderr=sys.stdout if False else log_path.open("a"),  # append stderr to same file
            text=True,
            check=False,
        )
        rc = proc.returncode
    except Exception as e:
        return Result(t, 2, log_path, f"ERROR: {e}", "")

    # read log for summary + snippet
    try:
        txt = log_path.read_text(errors="replace")
    except Exception:
        txt = ""

    summary = ""
    m = None
    for line in txt.splitlines():
        if SUMMARY_RE.search(line):
            m = line
    if m:
        summary = m.strip()
    else:
        summary = "(no summary match)"

    snippet = ""
    if show_fails:
        hits = []
        for i, line in enumerate(txt.splitlines(), start=1):
            if FAIL_SNIPPET_RE.search(line):
                hits.append(f"{i}:{line}")
            if len(hits) >= 60:
                break
        snippet = "\n".join(hits)

    return Result(t, rc, log_path, summary, snippet)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate Noise Engine packs/generators with parallel logs + summaries."
    )
    ap.add_argument(
        "targets",
        nargs="*",
        help='Targets: "pack_id" or "pack_id/gen_id". If omitted, checks all packs.',
    )
    ap.add_argument("--jobs", type=int, default=8, help="Parallel workers (default: 8)")
    ap.add_argument("--log-dir", default="/tmp/noise-validate", help="Where logs go")
    ap.add_argument("--render", action="store_true", help="Pass --render to validator")
    ap.add_argument("--env-mode", default="both", help='Validator env mode (default: "both")')
    ap.add_argument(
        "--extra",
        default="",
        help='Extra args passed to validator, e.g. --extra=\'--seconds 4 --strict\'',
    )
    ap.add_argument("--show-fails", action="store_true", help="Print failure snippets inline")
    args = ap.parse_args()

    root = repo_root()
    packs_dir = root / "packs"
    if not packs_dir.is_dir():
        print("ERROR: run from repo root (missing ./packs)", file=sys.stderr)
        return 2

    targets = parse_targets(args, packs_dir)
    log_dir = Path(args.log_dir)
    extra_args = shlex.split(args.extra) if args.extra else []

    results: List[Result] = []
    worst_rc = 0

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        futs = [
            ex.submit(
                run_validate_one,
                root,
                t,
                log_dir,
                args.render,
                args.env_mode,
                extra_args,
                args.show_fails,
            )
            for t in targets
        ]
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)

    # stable output order: by target ref
    results.sort(key=lambda r: r.target.ref)

    any_issues = False
    for r in results:
        if r.rc != 0:
            any_issues = True
        # if summary contains "issues found" treat as issues even if rc==0
        if re.search(r"issues found", r.summary, re.IGNORECASE):
            any_issues = True

        status = "OK"
        if r.rc != 0:
            status = f"ERROR(rc={r.rc})"
        elif re.search(r"issues found", r.summary, re.IGNORECASE):
            status = "ISSUES"

        print(f"{r.target.ref}: {status} — {r.summary} — log={r.log_path}")

        if args.show_fails and r.fail_snippet:
            print(r.fail_snippet)
            print("-" * 60)

    # exit code: 0 if clean, 1 if issues, 2 if errors (rc!=0)
    if any(r.rc != 0 for r in results):
        return 2
    if any_issues:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
