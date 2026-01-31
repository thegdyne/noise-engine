#!/usr/bin/env python3
"""
Scope Debug Plotter
Compares raw generator audio (from SC) with the scope buffer and Python display frame.

Usage:
    1. Press Ctrl+D in Noise Engine while scope is active
    2. Wait for "Scope debug capture" toast
    3. Run: python3 tools/scope_debug.py

This reads two CSV files from ~/Downloads:
    - scope_debug.csv       (from SC: raw intermediate bus audio + scope buffer)
    - scope_debug_python.csv (from Python: OSC buffer as received + trimmed display)

Plots 3 panels:
    1. Raw audio from intermediate bus (what the generator actually outputs)
    2. Scope buffer (what SC wrote into the triggered buffer)
    3. Python display (what the scope widget actually rendered)
"""

import csv
import os
import sys

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams['figure.facecolor'] = '#1a1a1a'
    matplotlib.rcParams['axes.facecolor'] = '#0a0c0a'
    matplotlib.rcParams['text.color'] = '#cccccc'
    matplotlib.rcParams['axes.labelcolor'] = '#cccccc'
    matplotlib.rcParams['xtick.color'] = '#888888'
    matplotlib.rcParams['ytick.color'] = '#888888'
except ImportError:
    print("ERROR: matplotlib is required. Install with: pip3 install matplotlib")
    sys.exit(1)

DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
SC_CSV = os.path.join(DOWNLOADS, "scope_debug.csv")
PY_CSV = os.path.join(DOWNLOADS, "scope_debug_python.csv")

TRACE_COLOR = '#00ff88'      # Phosphor green (matches scope)
RAW_COLOR = '#ff6400'        # Orange
GRID_COLOR = '#1a3a2a'


def read_sc_csv(path):
    """Read SC debug CSV: sample, raw_audio, scope_buffer."""
    raw_audio = []
    scope_buffer = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_val = row.get('raw_audio', '')
            scope_val = row.get('scope_buffer', '')
            raw_audio.append(float(raw_val) if raw_val != '' else None)
            scope_buffer.append(float(scope_val) if scope_val != '' else None)
    # Filter out None values for scope buffer
    scope_buffer = [v for v in scope_buffer if v is not None]
    return raw_audio, scope_buffer


def read_python_csv(path):
    """Read Python debug CSV: sample, raw_osc_buf, displayed, write_pos."""
    raw_osc = []
    displayed = []
    write_pos = 0
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_val = row.get('raw_osc_buf', '')
            disp_val = row.get('displayed', '')
            wp = row.get('write_pos', '')
            raw_osc.append(float(raw_val) if raw_val != '' else None)
            displayed.append(float(disp_val) if disp_val != '' else None)
            if wp != '':
                write_pos = int(float(wp))
    raw_osc = [v for v in raw_osc if v is not None]
    displayed = [v for v in displayed if v is not None]
    return raw_osc, displayed, write_pos


def plot_debug():
    """Main plotting function."""
    has_sc = os.path.exists(SC_CSV)
    has_py = os.path.exists(PY_CSV)

    if not has_sc and not has_py:
        print(f"No debug files found in {DOWNLOADS}")
        print("Press Ctrl+D in Noise Engine to trigger a capture.")
        sys.exit(1)

    # Count panels
    panels = 0
    if has_sc:
        panels += 2  # raw audio + scope buffer
    if has_py:
        panels += 1  # python display

    fig, axes = plt.subplots(panels, 1, figsize=(14, 3.5 * panels), sharex=False)
    if panels == 1:
        axes = [axes]

    panel_idx = 0

    # --- SC data ---
    if has_sc:
        raw_audio, scope_buffer = read_sc_csv(SC_CSV)
        print(f"SC raw audio: {len(raw_audio)} samples")
        print(f"SC scope buffer: {len(scope_buffer)} samples")

        # Panel 1: Raw intermediate bus audio
        ax = axes[panel_idx]
        ax.plot(raw_audio, color=RAW_COLOR, linewidth=0.8, alpha=0.9)
        ax.set_title("Raw Intermediate Bus Audio (from SC RecordBuf)",
                      color=RAW_COLOR, fontsize=11, fontweight='bold')
        ax.set_ylabel("Amplitude")
        ax.set_ylim(-1.1, 1.1)
        ax.axhline(0, color=GRID_COLOR, linewidth=0.5)
        ax.grid(True, color=GRID_COLOR, alpha=0.3)
        panel_idx += 1

        # Panel 2: Scope buffer
        ax = axes[panel_idx]
        ax.plot(scope_buffer, color=TRACE_COLOR, linewidth=1.2, alpha=0.9)
        ax.set_title("Scope Buffer (triggered, 1024 samples from BufWr)",
                      color=TRACE_COLOR, fontsize=11, fontweight='bold')
        ax.set_ylabel("Amplitude")
        ax.set_ylim(-1.1, 1.1)
        ax.axhline(0, color=GRID_COLOR, linewidth=0.5)
        ax.grid(True, color=GRID_COLOR, alpha=0.3)
        panel_idx += 1

    # --- Python data ---
    if has_py:
        raw_osc, displayed, write_pos = read_python_csv(PY_CSV)
        print(f"Python OSC buffer: {len(raw_osc)} samples")
        print(f"Python displayed: {len(displayed)} samples (write_pos={write_pos})")

        ax = axes[panel_idx]
        # Show the full OSC buffer dimmed, then the displayed portion bright
        ax.plot(raw_osc, color='#005533', linewidth=0.6, alpha=0.5, label='Full OSC buffer')
        ax.plot(displayed, color=TRACE_COLOR, linewidth=1.5, alpha=0.9, label='Displayed (trimmed)')
        if write_pos > 0:
            ax.axvline(write_pos, color='#ff6400', linewidth=1, linestyle='--',
                        alpha=0.7, label=f'write_pos={write_pos}')
        ax.set_title("Python Display (what the scope widget renders)",
                      color=TRACE_COLOR, fontsize=11, fontweight='bold')
        ax.set_ylabel("Amplitude")
        ax.set_ylim(-1.1, 1.1)
        ax.axhline(0, color=GRID_COLOR, linewidth=0.5)
        ax.grid(True, color=GRID_COLOR, alpha=0.3)
        ax.legend(loc='upper right', fontsize=8, facecolor='#1a1a1a', edgecolor='#333333')
        panel_idx += 1

    # Stats
    if has_sc and has_py:
        fig.text(0.5, 0.01,
                 f"SC raw: {len(raw_audio)} samples | SC scope buf: {len(scope_buffer)} | "
                 f"Python displayed: {len(displayed)} (write_pos={write_pos})",
                 ha='center', fontsize=9, color='#888888')

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    fig.suptitle("Scope Debug Capture", fontsize=14, fontweight='bold',
                  color=TRACE_COLOR, y=0.99)
    plt.show()


if __name__ == '__main__':
    plot_debug()
