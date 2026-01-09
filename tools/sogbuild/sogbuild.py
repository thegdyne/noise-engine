#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    print("ERROR: missing dependency PyYAML. Install: python3 -m pip install pyyaml", file=sys.stderr)
    raise


ROOT = Path(__file__).resolve().parent
SECDIR = ROOT / "sections"
BUILDDIR = ROOT / "build"
CFG_PATH = ROOT / "sections.yaml"


SECTION_MARK_RE = re.compile(r"^\s*//\s*===\s*SOGSECTION:\s*([A-Za-z0-9_\-\.]+)\s*===\s*$")

FORBID_WORDS_RE = re.compile(r"\b(and|or|not)\b")
# matches: "= ... - ("
FORBID_UNARY_ASSIGN_RE = re.compile(r'=\s*-\s*\(')


@dataclass
class LintHit:
    file: Path
    line_no: int
    col_no: int
    message: str
    line: str


def load_cfg() -> dict:
    if not CFG_PATH.exists():
        print(f"ERROR: missing config: {CFG_PATH}", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(CFG_PATH.read_text()) or {}


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="strict")


def write_text(p: Path, txt: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


def list_missing(order: list[str]) -> list[Path]:
    missing = []
    for name in order:
        p = SECDIR / name
        if not p.exists():
            missing.append(p)
    return missing


def lint_file(path: Path, forbid_words: bool, forbid_unary_assign: bool) -> list[LintHit]:
    hits: list[LintHit] = []
    lines = read_text(path).splitlines()

    for i, line in enumerate(lines, start=1):
        if forbid_words:
            for m in FORBID_WORDS_RE.finditer(line):
                hits.append(LintHit(path, i, m.start() + 1,
                                    "Use UGen masks (0/1), avoid language boolean ops. (and/or/not)",
                                    line))
        if forbid_unary_assign:
            for m in FORBID_UNARY_ASSIGN_RE.finditer(line):
                hits.append(LintHit(path, i, m.start() + 1,
                                    "Unary '-(' after assignment: prefer .neg to avoid parser edge cases.",
                                    line))
    return hits


def cmd_lint() -> int:
    cfg = load_cfg()
    lint_cfg = cfg.get("lint", {}) or {}
    forbid_words = bool(lint_cfg.get("forbid_words", True))
    forbid_unary_assign = bool(lint_cfg.get("forbid_unary_assign", True))

    asm = cfg.get("assemble", {}) or {}
    order = asm.get("order", []) or []
    if not order:
        print("ERROR: sections.yaml assemble.order is empty", file=sys.stderr)
        return 2

    missing = list_missing(order)
    if missing:
        print("Missing section files:", file=sys.stderr)
        for p in missing:
            print(str(p), file=sys.stderr)
        return 2

    hits: list[LintHit] = []
    for name in order:
        hits.extend(lint_file(SECDIR / name, forbid_words, forbid_unary_assign))

    if hits:
        # Print in rg-like format for copy/paste:
        # file:line:col: message
        for h in hits:
            print(f"{h.file.name}:{h.line_no}:{h.col_no}: {h.message}")
            print(f"    {h.line}")
        return 1

    print("OK: lint passed")
    return 0


def cmd_assemble() -> int:
    cfg = load_cfg()
    asm = cfg.get("assemble", {}) or {}
    out_file = asm.get("out_file", "build/00_all.scd")
    order = asm.get("order", []) or []

    if not order:
        print("ERROR: sections.yaml assemble.order is empty", file=sys.stderr)
        return 2

    missing = list_missing(order)
    if missing:
        print("Missing section files:", file=sys.stderr)
        for p in missing:
            print(str(p), file=sys.stderr)
        print("\nFix by either:", file=sys.stderr)
        print("1) creating those files, or", file=sys.stderr)
        print("2) updating sections.yaml assemble.order, or", file=sys.stderr)
        print("3) rerunning split/bootstrap from a monolith.", file=sys.stderr)
        return 2

    out_path = ROOT / out_file
    chunks: list[str] = []
    for name in order:
        p = SECDIR / name
        txt = read_text(p).rstrip()  # prevent runaway blank growth
        chunks.append(txt)

    final = "\n\n".join(chunks).rstrip() + "\n"
    write_text(out_path, final)
    print(f"OK: assembled -> {out_path}")
    return 0


def cmd_split(monolith: Path) -> int:
    if not monolith.exists():
        print(f"ERROR: monolith not found: {monolith}", file=sys.stderr)
        return 2

    lines = read_text(monolith).splitlines(keepends=False)

    # Parse sections by explicit markers:
    # // === SOGSECTION: 00_header.scd ===
    # content...
    current_name: str | None = None
    buf: list[str] = []
    sections: list[tuple[str, str]] = []

    def flush():
        nonlocal buf, current_name
        if current_name is None:
            return
        content = "\n".join(buf).rstrip() + "\n"
        sections.append((current_name, content))
        buf = []

    for line in lines:
        m = SECTION_MARK_RE.match(line)
        if m:
            flush()
            current_name = m.group(1)
            continue
        buf.append(line)

    flush()

    if not sections:
        print("ERROR: no SOGSECTION markers found. Add lines like:", file=sys.stderr)
        print("// === SOGSECTION: 00_header.scd ===", file=sys.stderr)
        return 2

    # Write section files
    order: list[str] = []
    for name, content in sections:
        order.append(name)
        write_text(SECDIR / name, content)

    # Update sections.yaml assemble.order to match the new split
    cfg = load_cfg()
    cfg.setdefault("assemble", {})
    cfg["assemble"]["order"] = order
    cfg["assemble"].setdefault("out_file", "build/00_all.scd")
    write_text(CFG_PATH, yaml.safe_dump(cfg, sort_keys=False))

    print("OK: split wrote section files:")
    for n in order:
        print(f" - {SECDIR / n}")
    print("OK: updated sections.yaml assemble.order")
    return 0


def cmd_prove(build_file: Path) -> int:
    runner = ROOT / "prove_runner.scd"
    if not runner.exists():
        print(f"ERROR: missing prove runner: {runner}", file=sys.stderr)
        return 2
    if not build_file.exists():
        print(f"ERROR: build file not found: {build_file}", file=sys.stderr)
        return 2

    cmd = ["sclang", str(runner), str(build_file)]
    print("RUN:", " ".join(cmd))
    p = subprocess.run(cmd, text=True)
    return p.returncode


def cmd_all() -> int:
    rc = cmd_lint()
    if rc != 0:
        return rc
    rc = cmd_assemble()
    if rc != 0:
        return rc
    cfg = load_cfg()
    out_file = (cfg.get("assemble", {}) or {}).get("out_file", "build/00_all.scd")
    out_path = (ROOT / out_file).resolve()
    return cmd_prove(out_path)


def main() -> None:
    ap = argparse.ArgumentParser(prog="sogbuild")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("lint")
    sub.add_parser("assemble")
    sp = sub.add_parser("split")
    sp.add_argument("monolith", type=str)

    pp = sub.add_parser("prove")
    pp.add_argument("build_file", type=str)

    sub.add_parser("all")

    args = ap.parse_args()

    if args.cmd == "lint":
        sys.exit(cmd_lint())
    if args.cmd == "assemble":
        sys.exit(cmd_assemble())
    if args.cmd == "split":
        sys.exit(cmd_split(Path(args.monolith).resolve()))
    if args.cmd == "prove":
        sys.exit(cmd_prove(Path(args.build_file).resolve()))
    if args.cmd == "all":
        sys.exit(cmd_all())

    sys.exit(2)


if __name__ == "__main__":
    main()
