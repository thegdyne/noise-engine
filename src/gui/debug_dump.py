"""
UI Debug Dump - generates full widget hierarchy with sizing info.
Run with: python -c "from src.gui.debug_dump import dump_ui; dump_ui()"

Hotkeys:
  F8  - Dump generator slots
  F12 - Dump modulator slots
  `   - Dump ALL + hotfix status report (backtick key)
"""

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QSize
import os
import json
from datetime import datetime


def widget_info(w):
    """Get detailed sizing info for a widget."""
    info = {
        'class': w.__class__.__name__,
        'objectName': w.objectName() or '(unnamed)',
        'pos': f"{w.x()},{w.y()}",
        'size': f"{w.width()}x{w.height()}",
        'sizeHint': fmt_size(w.sizeHint()),
        'minimumSizeHint': fmt_size(w.minimumSizeHint()),
        'minimumSize': fmt_size(w.minimumSize()),
        'maximumSize': fmt_size(w.maximumSize()),
        'fixedSize': is_fixed(w),
        'sizePolicy': fmt_policy(w.sizePolicy()),
        'visible': w.isVisible(),
    }
    return info


def fmt_size(s):
    if isinstance(s, QSize):
        return f"{s.width()}x{s.height()}"
    return str(s)


def fmt_policy(p):
    h = ['Fixed', 'Minimum', 'Maximum', 'Preferred', 'Expanding', 'MinimumExpanding', 'Ignored']
    hp = p.horizontalPolicy()
    vp = p.verticalPolicy()
    return f"H:{h[hp] if hp < len(h) else hp} V:{h[vp] if vp < len(h) else vp}"


def is_fixed(w):
    ms = w.minimumSize()
    xs = w.maximumSize()
    h_fixed = ms.width() == xs.width() and ms.width() > 0
    v_fixed = ms.height() == xs.height() and ms.height() > 0
    if h_fixed and v_fixed:
        return f"FIXED {ms.width()}x{ms.height()}"
    elif h_fixed:
        return f"H-FIXED {ms.width()}"
    elif v_fixed:
        return f"V-FIXED {ms.height()}"
    return ""


def dump_widget_tree(widget, indent=0, lines=None, filter_name=None):
    """Recursively dump widget tree."""
    if lines is None:
        lines = []

    info = widget_info(widget)

    # Skip invisible unless top-level
    if not info['visible'] and indent > 0:
        return lines

    # Filter check
    if filter_name and filter_name.lower() not in info['objectName'].lower():
        # Still recurse children
        for child in widget.children():
            if isinstance(child, QWidget) and child.parent() == widget:
                dump_widget_tree(child, indent, lines, filter_name)
        return lines

    prefix = "  " * indent

    # Compact format
    fixed_marker = f" ⚠️{info['fixedSize']}" if info['fixedSize'] else ""
    line = f"{prefix}{info['objectName']} ({info['class']}) @{info['pos']} {info['size']}{fixed_marker}"
    lines.append(line)

    # Details on next line if interesting
    details = []
    if info['sizeHint'] != info['size']:
        details.append(f"hint:{info['sizeHint']}")
    if info['minimumSize'] != "0x0":
        details.append(f"min:{info['minimumSize']}")
    if details:
        lines.append(f"{prefix}  └─ {' | '.join(details)} | {info['sizePolicy']}")

    # Recurse children (direct only)
    for child in widget.children():
        if isinstance(child, QWidget) and child.parent() == widget:
            dump_widget_tree(child, indent + 1, lines, filter_name=None)  # Don't filter children

    return lines


def dump_mod_slots():
    """Dump just the modulator slot hierarchy."""
    app = QApplication.instance()
    if not app:
        print("No QApplication running")
        return

    # Find main window
    for w in app.topLevelWidgets():
        if w.__class__.__name__ == 'MainFrame':
            # Find ModulatorGrid
            for child in w.findChildren(QWidget):
                if child.__class__.__name__ == 'ModulatorGrid':
                    lines = dump_widget_tree(child)
                    output = '\n'.join(lines)

                    # Write to file
                    outpath = os.path.expanduser('~/Downloads/mod_slots_dump.txt')
                    with open(outpath, 'w') as f:
                        f.write(output)

                    print(output)
                    print(f"\n\nSaved to {outpath}")
                    return

    print("ModulatorGrid not found")


def dump_gen_slots():
    """Dump just the generator slot hierarchy."""
    app = QApplication.instance()
    if not app:
        print("No QApplication running")
        return

    # Find main window
    for w in app.topLevelWidgets():
        if w.__class__.__name__ == 'MainFrame':
            # Find GeneratorGrid
            for child in w.findChildren(QWidget):
                if child.__class__.__name__ == 'GeneratorGrid':
                    lines = dump_widget_tree(child)
                    output = '\n'.join(lines)

                    # Write to file
                    outpath = os.path.expanduser('~/Downloads/gen_slots_dump.txt')
                    with open(outpath, 'w') as f:
                        f.write(output)

                    print(output)
                    print(f"\n\nSaved to {outpath}")
                    return

    print("GeneratorGrid not found")


def dump_ui():
    """Dump full UI hierarchy."""
    app = QApplication.instance()
    if not app:
        print("No QApplication running")
        return

    for w in app.topLevelWidgets():
        if w.__class__.__name__ == 'MainFrame':
            lines = dump_widget_tree(w)
            output = '\n'.join(lines)

            with open('/tmp/ui_dump.txt', 'w') as f:
                f.write(output)

            print(f"Dumped {len(lines)} lines to /tmp/ui_dump.txt")
            return


# === HOTFIX STATUS CHECKS ===

def check_fx_widths():
    """HF-3: Check FX module widths."""
    app = QApplication.instance()
    if not app:
        return {}

    widths = {}
    for w in app.topLevelWidgets():
        if w.__class__.__name__ == 'MainFrame':
            # Find InlineFXStrip
            for child in w.findChildren(QWidget):
                name = child.objectName()
                if child.__class__.__name__ in ('EffectModule', 'QFrame'):
                    # Check for fx modules by objectName pattern
                    if name in ('heat', 'echo', 'reverb', 'filter') or 'fx_' in name:
                        widths[name or child.__class__.__name__] = child.width()
                # Also check by attribute names on InlineFXStrip
                if child.__class__.__name__ == 'InlineFXStrip':
                    for attr in ('heat', 'echo', 'reverb', 'filter'):
                        if hasattr(child, attr):
                            mod = getattr(child, attr)
                            widths[attr] = mod.width()
    return widths


def check_grid_cols():
    """HF-6: Check boid visualizer GRID_COLS."""
    app = QApplication.instance()
    if not app:
        return None

    for w in app.topLevelWidgets():
        if w.__class__.__name__ == 'MainFrame':
            for child in w.findChildren(QWidget):
                if child.__class__.__name__ == 'BoidMiniVisualizer':
                    # Check class attribute
                    return getattr(child.__class__, 'GRID_COLS', None)
    return None


def check_unnamed_widgets():
    """HF-4: Count widgets without objectName."""
    app = QApplication.instance()
    if not app:
        return {'total': 0, 'unnamed': 0}

    total = 0
    unnamed = 0
    unnamed_list = []

    for w in app.topLevelWidgets():
        if w.__class__.__name__ == 'MainFrame':
            for child in w.findChildren(QWidget):
                total += 1
                if not child.objectName():
                    unnamed += 1
                    if len(unnamed_list) < 20:  # Cap list
                        unnamed_list.append(f"{child.__class__.__name__} in {child.parent().__class__.__name__ if child.parent() else 'root'}")

    return {'total': total, 'unnamed': unnamed, 'examples': unnamed_list}


def collect_widget_geometry(main_window):
    """Collect all widget positions/sizes as dict for JSON export."""
    widgets = {}

    for child in main_window.findChildren(QWidget):
        name = child.objectName()
        if name:  # Only named widgets
            # Get global position
            pos = child.mapToGlobal(child.rect().topLeft())
            widgets[name] = {
                'class': child.__class__.__name__,
                'x': child.x(),
                'y': child.y(),
                'w': child.width(),
                'h': child.height(),
                'global_x': pos.x(),
                'global_y': pos.y(),
                'visible': child.isVisible()
            }

    return widgets


def dump_all():
    """Dump ALL UI state + hotfix status report."""
    app = QApplication.instance()
    if not app:
        print("No QApplication running")
        return

    main_window = None
    for w in app.topLevelWidgets():
        if w.__class__.__name__ == 'MainFrame':
            main_window = w
            break

    if not main_window:
        print("MainFrame not found")
        return

    outdir = os.path.expanduser('~/Downloads')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # === TEXT REPORT ===
    lines = []
    lines.append("=" * 60)
    lines.append("UI STATE DUMP + HOTFIX STATUS")
    lines.append(f"Timestamp: {datetime.now().isoformat()}")
    lines.append("=" * 60)

    # Hotfix status
    lines.append("\n### HOTFIX STATUS ###\n")

    # HF-3: FX widths
    fx_widths = check_fx_widths()
    lines.append("HF-3 FX Module Widths (target: all 145px):")
    if fx_widths:
        all_145 = all(w == 145 for w in fx_widths.values())
        status = "✅ DONE" if all_145 else "❌ NOT DONE"
        lines.append(f"  Status: {status}")
        for name, width in sorted(fx_widths.items()):
            marker = "✓" if width == 145 else "✗"
            lines.append(f"    {marker} {name}: {width}px")
    else:
        lines.append("  (could not find FX modules)")

    # HF-6: Grid cols
    grid_cols = check_grid_cols()
    lines.append(f"\nHF-6 Boid GRID_COLS (target: 176):")
    if grid_cols == 176:
        lines.append(f"  Status: ✅ DONE ({grid_cols})")
    elif grid_cols:
        lines.append(f"  Status: ❌ NOT DONE ({grid_cols})")
    else:
        lines.append("  (could not find BoidMiniVisualizer)")

    # HF-4: Unnamed widgets
    unnamed = check_unnamed_widgets()
    lines.append(f"\nHF-4 Widget objectName Coverage:")
    lines.append(f"  Total widgets: {unnamed['total']}")
    lines.append(f"  Unnamed: {unnamed['unnamed']} ({100*unnamed['unnamed']//max(1,unnamed['total'])}%)")
    if unnamed.get('examples'):
        lines.append("  Examples of unnamed:")
        for ex in unnamed['examples'][:10]:
            lines.append(f"    - {ex}")

    # HF-10: Would need to grep source files, skip for runtime check
    lines.append(f"\nHF-10 Hardcoded Colors:")
    lines.append("  (run: grep -rln '#[0-9a-fA-F]{{6}}' src/gui/*.py | grep -v theme.py)")

    lines.append("\n" + "=" * 60)
    lines.append("WIDGET HIERARCHY")
    lines.append("=" * 60 + "\n")

    # Full widget tree
    tree_lines = dump_widget_tree(main_window)
    lines.extend(tree_lines)

    # Write text report
    txt_path = os.path.join(outdir, f'ui_dump_{timestamp}.txt')
    with open(txt_path, 'w') as f:
        f.write('\n'.join(lines))

    # === JSON EXPORT ===
    json_data = {
        'timestamp': datetime.now().isoformat(),
        'hotfix_status': {
            'HF3_fx_widths': fx_widths,
            'HF3_all_145': all(w == 145 for w in fx_widths.values()) if fx_widths else False,
            'HF6_grid_cols': grid_cols,
            'HF6_done': grid_cols == 176,
            'HF4_total_widgets': unnamed['total'],
            'HF4_unnamed_widgets': unnamed['unnamed'],
        },
        'widgets': collect_widget_geometry(main_window)
    }

    json_path = os.path.join(outdir, f'ui_state_{timestamp}.json')
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)

    # Also write a "latest" symlink/copy for easy access
    latest_txt = os.path.join(outdir, 'ui_dump_latest.txt')
    latest_json = os.path.join(outdir, 'ui_state_latest.json')

    # Copy to latest (symlinks can be annoying on some systems)
    with open(latest_txt, 'w') as f:
        f.write('\n'.join(lines))
    with open(latest_json, 'w') as f:
        json.dump(json_data, f, indent=2)

    print(f"\n{'='*50}")
    print("UI DUMP COMPLETE")
    print(f"{'='*50}")
    print(f"Text report: {txt_path}")
    print(f"JSON state:  {json_path}")
    print(f"Latest:      {latest_txt}")
    print(f"{'='*50}\n")

    # Print summary to console
    print("HOTFIX SUMMARY:")
    print(f"  HF-3 FX widths:  {'✅' if json_data['hotfix_status']['HF3_all_145'] else '❌'} {fx_widths}")
    print(f"  HF-6 GRID_COLS:  {'✅' if json_data['hotfix_status']['HF6_done'] else '❌'} {grid_cols}")
    print(f"  HF-4 Unnamed:    {unnamed['unnamed']}/{unnamed['total']} widgets")


# Hook into running app - call from console or add hotkey
def install_dump_hotkey(main_window):
    """Install F8/F12/Shift+F8 hotkeys to dump widget hierarchies."""
    from PyQt5.QtWidgets import QShortcut
    from PyQt5.QtGui import QKeySequence

    shortcut_mod = QShortcut(QKeySequence('F12'), main_window)
    shortcut_mod.activated.connect(dump_mod_slots)

    shortcut_gen = QShortcut(QKeySequence('F8'), main_window)
    shortcut_gen.activated.connect(dump_gen_slots)

    shortcut_all = QShortcut(QKeySequence('`'), main_window)
    shortcut_all.activated.connect(dump_all)

    print("F8 hotkey installed - dump generator slots")
    print("F12 hotkey installed - dump modulator slots")
    print("` (backtick) hotkey installed - dump ALL + hotfix status")