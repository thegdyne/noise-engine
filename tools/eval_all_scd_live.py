#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
from pathlib import Path


def find_scd(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.scd") if p.is_file())


def excluded(path_str: str, excludes: list[str]) -> bool:
    return any(x in path_str for x in excludes)


def resolve_path(root: Path, p: str) -> Path:
    pp = Path(p).expanduser()
    if pp.is_absolute():
        return pp.resolve()
    return (root / pp).resolve()


def run_one_live(
    sclang: str,
    runner: Path,
    preload: str,
    target: Path,
    timeout_sec: float,
    echo_cmd: bool,
) -> tuple[int, float, str]:
    cmd = [sclang, str(runner), preload, str(target)]
    if echo_cmd:
        print("CMD:", " ".join(cmd), flush=True)

    start = time.time()
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered
    )

    lines: list[str] = []
    try:
        assert p.stdout is not None

        # Stream output live
        for line in p.stdout:
            lines.append(line)
            sys.stdout.write("  | " + line)
            sys.stdout.flush()

        # Ensure we don't wait beyond timeout (in case stdout closes early)
        elapsed = time.time() - start
        remaining = max(0.0, timeout_sec - elapsed)
        rc = p.wait(timeout=remaining)

        dur = time.time() - start
        return rc, dur, "".join(lines)

    except subprocess.TimeoutExpired:
        dur = time.time() - start
        p.kill()
        try:
            out_rest = p.communicate(timeout=1)[0] or ""
        except Exception:
            out_rest = ""
        lines.append("\nTIMEOUT\n")
        lines.append(out_rest)
        return 124, dur, "".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="Project root to scan")
    ap.add_argument("--sclang", default="sclang", help="Path to sclang (default: sclang)")
    ap.add_argument("--runner", default="tools/sc_eval_one.scd", help="Runner .scd (repo-relative or absolute)")
    ap.add_argument(
        "--preload",
        default="-",
        help="Project init .scd to load before each target (repo-relative or absolute), or '-' for none",
    )
    ap.add_argument("--timeout", type=float, default=12.0, help="Per-file timeout (sec)")
    ap.add_argument("--exclude", action="append", default=[], help="Substring excludes (repeatable)")
    ap.add_argument("--only", default="", help="Only run files whose path contains this substring")
    ap.add_argument("--stop-on-fail", action="store_true", help="Stop at first failure/timeout")
    ap.add_argument("--echo-cmd", action="store_true", help="Print the exact sclang command per file")
    ap.add_argument("--show-tail", type=int, default=120, help="Tail lines to print for each problem file")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()

    runner_path = resolve_path(root, args.runner)
    if not runner_path.exists():
        print(f"Runner not found: {runner_path}", file=sys.stderr)
        return 3

    preload_arg = args.preload
    if preload_arg != "-":
        preload_path = resolve_path(root, preload_arg)
        if not preload_path.exists():
            print(f"Preload not found: {preload_path}", file=sys.stderr)
            return 4
        preload_arg = str(preload_path)

    files = find_scd(root)

    if args.exclude:
        files = [p for p in files if not excluded(str(p), args.exclude)]
    if args.only:
        files = [p for p in files if args.only in str(p)]

    print(f"Scanning : {root}", flush=True)
    print(f"Runner   : {runner_path}", flush=True)
    print(f"Preload  : {preload_arg}", flush=True)
    print(f"Found    : {len(files)} .scd files\n", flush=True)

    ok: list[Path] = []
    problems: list[tuple[Path, int, float, str]] = []

    for i, pth in enumerate(files, start=1):
        print(f"[{i}/{len(files)}] {pth}", flush=True)
        rc, dur, out = run_one_live(
            args.sclang, runner_path, preload_arg, pth, args.timeout, args.echo_cmd
        )
        status = "OK" if rc == 0 else ("TIMEOUT" if rc == 124 else "FAIL")
        print(f"--> {status} (rc={rc}) in {dur:.2f}s\n", flush=True)

        if rc == 0:
            ok.append(pth)
        else:
            problems.append((pth, rc, dur, out))
            if args.stop_on_fail:
                break

    print("\n=== SUMMARY ===", flush=True)
    print(f"OK       : {len(ok)}", flush=True)
    print(f"PROBLEM  : {len(problems)}", flush=True)

    if problems:
        print("\n=== PROBLEMS (first 10) ===", flush=True)
        for pth, rc, dur, out in problems[:10]:
            print(f"\n--- {pth} (rc={rc}, {dur:.2f}s) ---", flush=True)
            tail = out.splitlines()[-args.show_tail :]
            print("\n".join(tail), flush=True)

    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
