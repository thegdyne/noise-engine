#!/usr/bin/env python3
"""
Generate a full showcase set into ~/Pictures/showcase/imaginarium/

- styles/: every STYLES key across a grid of brightness/noisiness
- presets/: every PRESETS key (one each)
"""

from __future__ import annotations

from pathlib import Path
from itertools import product

from imaginarium.tools.gen_test_image import STYLES, PRESETS, generate_test_image


def main() -> int:
    base = Path.home() / "Pictures" / "showcase" / "imaginarium"
    styles_dir = base / "styles"
    presets_dir = base / "presets"
    styles_dir.mkdir(parents=True, exist_ok=True)
    presets_dir.mkdir(parents=True, exist_ok=True)

    # 3x3 grid: low / mid / high
    bvals = [0.15, 0.50, 0.85]
    nvals = [0.10, 0.50, 0.90]

    size = (512, 512)

    # --- styles ---
    i = 0
    for style in STYLES.keys():
        for b, n in product(bvals, nvals):
            out = styles_dir / f"{style}_b{b:.2f}_n{n:.2f}.png"
            img = generate_test_image(
                brightness=b,
                noisiness=n,
                size=size,
                style=style,
                seed=42000 + i,
            )
            img.save(out)
            print(out)
            i += 1

    # --- presets ---
    for preset, params in PRESETS.items():
        out = presets_dir / f"{preset}.png"
        img = generate_test_image(
            brightness=float(params["brightness"]),
            noisiness=float(params["noisiness"]),
            size=size,
            style=str(params.get("style", "auto")),
            seed=4242,
        )
        img.save(out)
        print(out)

    print(f"\nDone. Output: {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

