"""
Theme - Centralized color and style definitions
All UI components reference this for consistent styling

RULE: All sliders must be vertical - no horizontal sliders
"""
import platform

# === FONTS ===
FONT_FAMILY = 'Helvetica'
MONO_FONT = 'Menlo' if platform.system() == 'Darwin' else 'Courier New'

FONT_SIZES = {
    'display': 32,    # Large displays (BPM)
    'title': 16,      # Main titles (NOISE ENGINE)
    'section': 12,    # Section headers (MIXER, EFFECTS)
    'slot_title': 11, # Generator/effect slot titles
    'label': 10,      # Labels
    'small': 9,       # Smaller labels
    'tiny': 8,        # Button text, values
    'micro': 7,       # Smallest text (mute/solo buttons)
}

# Drag/scroll sensitivity settings
DRAG_SENSITIVITY = {
    'slider_normal': 100,
    'slider_fine': 400,
    'cycle_normal': 15,
    'cycle_fine': 40,
    'generator_normal': 5,
    'generator_fine': 12,
    'bpm_value_normal': 3,
    'bpm_value_fine': 35,
}

# Base colors
COLORS = {
    # States
    'enabled': '#335533',
    'enabled_text': '#88ff88',
    'enabled_hover': '#446644',
    'disabled': '#333',
    'disabled_text': '#666',
    'inactive': '#222',
    'inactive_text': '#444',
    
    # Semantic colors
    'active': '#335533',
    'active_text': '#88ff88',
    'active_bg': '#1a2a1a',
    'submenu': '#553311',
    'submenu_text': '#ff8833',
    'submenu_hover': '#664422',
    'selected': '#333355',
    'selected_text': '#8888ff',
    'warning': '#553333',
    'warning_text': '#ff8888',
    'warning_hover': '#664444',
    
    # UI elements
    'background': '#1a1a1a',
    'background_dark': '#0a0a0a',
    'background_light': '#222',
    'background_highlight': '#2a2a2a',
    'border': '#333',
    'border_light': '#555',
    'border_active': '#44aa44',
    'text': '#888',
    'text_bright': '#aaa',
    'text_dim': '#555',
    'text_label': '#666',
    
    # Special displays
    'bpm_text': '#ff3333',
    
    # Indicators
    'audio_on': '#44ff44',
    'audio_off': '#555',
    'midi_on': '#ffaa00',
    'midi_off': '#555',
    'clock_pulse': '#44ff44',
    
    # Generator controls (skinnable)
    'mute_on': '#ff4444',
    'mute_on_text': '#ffffff',
    'mute_off': '#442222',
    'mute_off_text': '#884444',
    'gate_on': '#44ff44',
    'gate_off': '#223322',
    'midi_ch_bg': '#222244',
    'midi_ch_text': '#8888ff',
    'midi_ch_off_bg': '#222',
    'midi_ch_off_text': '#555',
    
    # Sliders/controls
    'slider_groove': '#333',
    'slider_handle': '#888',
    'slider_handle_hover': '#aaa',
    
    # WIP (Work In Progress) panels
    'wip_bg': '#151515',
    'wip_bg_light': '#1a1a1a',
    'wip_border': '#252525',
    'wip_text': '#383838',
    'wip_text_dim': '#444',
}

# Override specific component colors if needed
COMPONENT_COLORS = {}


def get_color(key, component=None):
    """Get color by key, with optional component-specific override."""
    if component:
        component_key = f"{component}.{key}"
        if component_key in COMPONENT_COLORS:
            return COMPONENT_COLORS[component_key]
    return COLORS.get(key, '#ff00ff')


def button_style(state='disabled'):
    """Get button stylesheet for state: enabled, disabled, submenu, inactive, warning."""
    if state == 'enabled':
        return f"""
            QPushButton {{
                background-color: {COLORS['enabled']};
                color: {COLORS['enabled_text']};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['enabled_hover']};
            }}
        """
    elif state == 'submenu':
        return f"""
            QPushButton {{
                background-color: {COLORS['submenu']};
                color: {COLORS['submenu_text']};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['submenu_hover']};
            }}
        """
    elif state == 'warning':
        return f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: {COLORS['warning_text']};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['warning_hover']};
            }}
        """
    elif state == 'inactive':
        return f"""
            QPushButton {{
                background-color: {COLORS['inactive']};
                color: {COLORS['inactive_text']};
                border-radius: 3px;
            }}
        """
    else:
        return f"""
            QPushButton {{
                background-color: {COLORS['disabled']};
                color: {COLORS['disabled_text']};
                border-radius: 3px;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['inactive']};
                color: {COLORS['inactive_text']};
            }}
        """


def slider_style():
    """Get standard vertical slider stylesheet."""
    return f"""
        QSlider::groove:vertical {{
            border: 1px solid {COLORS['border_light']};
            width: 8px;
            background: {COLORS['slider_groove']};
            border-radius: 4px;
        }}
        QSlider::handle:vertical {{
            background: {COLORS['slider_handle']};
            border: 1px solid {COLORS['border_light']};
            height: 12px;
            margin: 0 -3px;
            border-radius: 6px;
        }}
        QSlider::handle:vertical:hover {{
            background: {COLORS['slider_handle_hover']};
        }}
    """


def slider_style_center_notch():
    """
    Vertical slider with center notch mark.
    Use for sliders with a meaningful center position (e.g. EQ at 0dB).
    Shows a visual tick at the midpoint to indicate double-click reset target.
    """
    return f"""
        QSlider::groove:vertical {{
            border: 1px solid {COLORS['border_light']};
            width: 8px;
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 {COLORS['slider_groove']},
                stop:0.48 {COLORS['slider_groove']},
                stop:0.49 {COLORS['border_light']},
                stop:0.51 {COLORS['border_light']},
                stop:0.52 {COLORS['slider_groove']},
                stop:1 {COLORS['slider_groove']}
            );
            border-radius: 4px;
        }}
        QSlider::handle:vertical {{
            background: {COLORS['slider_handle']};
            border: 1px solid {COLORS['border_light']};
            height: 12px;
            margin: 0 -3px;
            border-radius: 6px;
        }}
        QSlider::handle:vertical:hover {{
            background: {COLORS['slider_handle_hover']};
        }}
    """


def pan_slider_style():
    """
    Horizontal pan slider with center notch mark.
    Compact style for channel strips.
    """
    return f"""
        QSlider::groove:horizontal {{
            height: 4px;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {COLORS['background_dark']},
                stop:0.48 {COLORS['background_dark']},
                stop:0.49 {COLORS['border_light']},
                stop:0.51 {COLORS['border_light']},
                stop:0.52 {COLORS['background_dark']},
                stop:1 {COLORS['background_dark']}
            );
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            width: 8px;
            height: 12px;
            margin: -4px 0;
            background: {COLORS['text_dim']};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {COLORS['text']};
        }}
    """


# === SKINNABLE GENERATOR CONTROL STYLES ===
# These are separated for future skin system

def mute_button_style(muted=False):
    """Mute button style - bright red when muted."""
    if muted:
        return f"""
            QPushButton {{
                background-color: {COLORS['mute_on']};
                color: {COLORS['mute_on_text']};
                border-radius: 3px;
                font-weight: bold;
            }}
        """
    else:
        return f"""
            QPushButton {{
                background-color: {COLORS['mute_off']};
                color: {COLORS['mute_off_text']};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #553333;
            }}
        """


def gate_indicator_style(active=False):
    """Gate LED indicator - flashes green on triggers."""
    if active:
        return f"""
            QLabel {{
                background-color: {COLORS['gate_on']};
                border-radius: 4px;
                border: 1px solid #66ff66;
            }}
        """
    else:
        return f"""
            QLabel {{
                background-color: {COLORS['gate_off']};
                border-radius: 4px;
                border: 1px solid #334433;
            }}
        """


def midi_channel_style(active=True):
    """MIDI channel button style."""
    if active:
        return f"""
            QPushButton {{
                background-color: {COLORS['midi_ch_bg']};
                color: {COLORS['midi_ch_text']};
                border-radius: 3px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #333366;
            }}
        """
    else:
        return f"""
            QPushButton {{
                background-color: {COLORS['midi_ch_off_bg']};
                color: {COLORS['midi_ch_off_text']};
                border-radius: 3px;
            }}
        """


def wip_panel_style():
    """Style for Work-In-Progress panels - heavily dimmed, no color."""
    return f"""
        QWidget {{
            background-color: {COLORS['wip_bg']};
        }}
        QLabel {{
            color: {COLORS['wip_text_dim']};
        }}
        QPushButton {{
            background-color: {COLORS['wip_bg_light']};
            color: {COLORS['wip_text']};
            border: 1px solid {COLORS['wip_border']};
        }}
        QPushButton:hover {{
            background-color: {COLORS['wip_bg_light']};
            color: {COLORS['wip_text']};
        }}
        QSlider::groove:vertical {{
            background: {COLORS['wip_bg_light']};
            border: 1px solid {COLORS['wip_border']};
        }}
        QSlider::handle:vertical {{
            background: {COLORS['disabled']};
            border: 1px solid {COLORS['wip_border']};
        }}
        QSlider::handle:vertical:hover {{
            background: {COLORS['disabled']};
        }}
        QFrame {{
            background-color: {COLORS['wip_bg']};
            border: 1px solid {COLORS['wip_border']};
        }}
    """


def wip_badge_style():
    """Style for the 'Coming Soon' badge - more prominent."""
    return f"""
        QLabel {{
            background-color: #442200;
            color: #aa6600;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 10px;
            font-weight: bold;
        }}
    """
