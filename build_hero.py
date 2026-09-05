"""Generate the animated isometric BEV-occupancy hero banner for the profile README.

The visual: an isometric grid of cells, like a bird's-eye-view occupancy map.
A sweep passes left to right; cells resolve from scattered noise into a coherent
occupied region, then fade back. Pure SVG + SMIL, so it animates on GitHub
without JavaScript.

Deterministic: the seed is fixed, so re-running produces byte-identical output.

Usage:  python build_hero.py
Writes: hero-dark.svg, hero-light.svg
"""
from __future__ import annotations

import random

W, H = 1200, 340          # viewBox
LAT, DEPTH = 28, 26       # lateral half-width, depth rows (l+d even = tessellating lattice)
CW, CH = 38, 19           # cell width / height in iso space
SWEEP = 6.0               # seconds for one full sweep

THEMES = {
    "dark": dict(
        bg="#0d1117", empty="#161b22", stroke="#21262d",
        low="#0d419d", mid="#1f6feb", high="#58a6ff", spark="#7ee787",
        title="#e6edf3", sub="#8b949e", rule="#30363d",
    ),
    "light": dict(
        bg="#ffffff", empty="#f0f3f6", stroke="#d0d7de",
        low="#b6e3ff", mid="#54aeff", high="#0969da", spark="#1a7f37",
        title="#1f2328", sub="#59636e", rule="#d1d9e0",
    ),
}


def occupancy(seed: int = 7) -> dict[tuple[int, int], float]:
    """A field in [0,1] over (lateral, depth) that reads as an occupancy map.

    Three soft returns, like vehicles at different ranges, over a low noise
    floor, so the resolved state looks like structure emerging rather than
    random sparkle. Keyed by grid coordinate.
    """
    rng = random.Random(seed)
    blobs = [(-17.0, 8.0, 3.2), (-5.0, 15.0, 3.8), (7.0, 10.0, 3.0), (19.0, 16.0, 3.4)]
    field: dict[tuple[int, int], float] = {}
    for d in range(DEPTH):
        for l in range(-LAT, LAT + 1):
            v = rng.random() * 0.13
            for bl, bd, br in blobs:
                dist2 = ((l - bl) * 0.70) ** 2 + ((d - bd) * 0.62) ** 2
                v += 1.05 * pow(2.718281828, -dist2 / (2 * br * br))
            field[(l, d)] = min(1.0, v)
    return field


def build(theme_name: str) -> str:
    c = THEMES[theme_name]
    field = occupancy()

    ox = W / 2
    oy = 138

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="Akila Lourdes Miriyala Francis, machine learning engineer">'
    )
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')

    # Vignette so the grid fades at the edges instead of ending abruptly.
    parts.append(
        f'<defs><radialGradient id="vig" cx="50%" cy="66%" r="78%">'
        f'<stop offset="62%" stop-color="{c["bg"]}" stop-opacity="0"/>'
        f'<stop offset="100%" stop-color="{c["bg"]}" stop-opacity="1"/>'
        f'</radialGradient></defs>'
    )

    cells: list[str] = []
    for d in range(DEPTH):
        for l in range(-LAT, LAT + 1):
            if (l + d) % 2:
                continue
            x = ox + l * CW / 2
            y = oy + d * CH / 2
            pts = (f'{x:.1f},{y:.1f} {x + CW/2:.1f},{y + CH/2:.1f} '
                   f'{x:.1f},{y + CH:.1f} {x - CW/2:.1f},{y + CH/2:.1f}')

            v = field[(l, d)]
            fill = c["empty"] if v < 0.32 else c["low"] if v < 0.55 else c["mid"] if v < 0.80 else c["high"]

            # Sweep phase: cells resolve left to right, with nearer rows lagging
            # slightly so the wavefront reads as a scan rather than a wipe.
            phase = ((l + LAT) + d * 0.30) / (2 * LAT + DEPTH * 0.30)
            begin = phase * SWEEP * 0.62
            peak = 0.14 + 0.86 * v

            cells.append(
                f'<polygon points="{pts}" fill="{fill}" opacity="0.06">'
                f'<animate attributeName="opacity" values="0.06;{peak:.2f};{peak*0.72:.2f};0.06" '
                f'keyTimes="0;0.18;0.62;1" dur="{SWEEP}s" begin="{begin:.2f}s" '
                f'repeatCount="indefinite"/></polygon>'
            )
    parts.append(f'<g stroke="{c["stroke"]}" stroke-width="0.5">')
    parts.extend(cells)
    parts.append('</g>')

    # Sweep bar: a soft vertical band travelling across the grid.
    parts.append(
        f'<defs><linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{c["spark"]}" stop-opacity="0"/>'
        f'<stop offset="50%" stop-color="{c["spark"]}" stop-opacity="0.30"/>'
        f'<stop offset="100%" stop-color="{c["spark"]}" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'<rect x="-170" y="130" width="170" height="210" fill="url(#sweep)">'
        f'<animate attributeName="x" values="-160;{W}" dur="{SWEEP}s" '
        f'repeatCount="indefinite"/></rect>'
    )

    parts.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')

    # Wordmark.
    parts.append(
        f'<text x="52" y="74" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
        f'font-size="34" font-weight="600" fill="{c["title"]}" letter-spacing="1.5">'
        f'AKILA LOURDES MIRIYALA FRANCIS</text>'
    )
    parts.append(f'<rect x="54" y="90" width="86" height="2" fill="{c["spark"]}"/>')
    parts.append(
        f'<text x="52" y="118" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
        f'font-size="15" fill="{c["sub"]}" letter-spacing="2.6">'
        f'MACHINE LEARNING ENGINEER · PERCEPTION · RETRIEVAL · EVALUATION</text>'
    )
    parts.append(f'<rect x="0" y="{H-2}" width="{W}" height="2" fill="{c["rule"]}"/>')
    parts.append('</svg>')
    return "".join(parts)


if __name__ == "__main__":
    for name in THEMES:
        out = f"hero-{name}.svg"
        with open(out, "w", encoding="utf-8") as f:
            f.write(build(name))
        print(f"wrote {out}")
