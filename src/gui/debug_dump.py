"""
UI Debug Dump - generates full widget hierarchy with sizing info.
Run with: python -c "from src.gui.debug_dump import dump_ui; dump_ui()"
"""

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QSize


def widget_info(w):
    """Get detailed sizing info for a widget."""
    info = {
        'class': w.__class__.__name__,
        'objectName': w.objectName() or '(unnamed)',
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
    line = f"{prefix}{info['objectName']} ({info['class']}) {info['size']}{fixed_marker}"
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
                    with open('/tmp/mod_slots_dump.txt', 'w') as f:
                        f.write(output)

                    print(output)
                    print(f"\n\nSaved to /tmp/mod_slots_dump.txt")
                    return

    print("ModulatorGrid not found")


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


# Hook into running app - call from console or add hotkey
def install_dump_hotkey(main_window):
    """Install F12 hotkey to dump mod slots."""
    from PyQt5.QtWidgets import QShortcut
    from PyQt5.QtGui import QKeySequence

    shortcut = QShortcut(QKeySequence('F12'), main_window)
    shortcut.activated.connect(dump_mod_slots)
    print("F12 hotkey installed - press to dump mod slot hierarchy")