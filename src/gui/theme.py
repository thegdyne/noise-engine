"""
Theme - Centralized color and style definitions
All UI components reference this for consistent styling

RULE: All sliders must be vertical - no horizontal sliders
"""
import platform

MONO_FONT = 'Menlo' if platform.system() == 'Darwin' else 'Courier New'

# Drag/scroll sensitivity settings
DRAG_SENSITIVITY = {
    'slider_normal': 100,          # Pixels for full slider range (0-1000)
    'slider_fine': 400,            # Pixels for full range with Shift
    'cycle_normal': 15,            # Pixels per step for CycleButton
    'cycle_fine': 40,              # Pixels per step with Shift
    'bpm_value_normal': 3,         # Pixels per BPM
    'bpm_value_fine': 35,          # Pixels per BPM with Shift
}

# Base colors
COLORS = {
    # States
    'enabled': '#335533',
    'enabled_text': '#88ff88',
    'disabled': '#333',
    'disabled_text': '#666',
    'inactive': '#222',
    'inactive_text': '#444',
    
    # Semantic colors
    'active': '#335533',
    'active_text': '#88ff88',
    'submenu': '#553311',
    'submenu_text': '#ff8833',
    'selected': '#333355',
    'selected_text': '#8888ff',
    'warning': '#553333',
    'warning_text': '#ff8888',
    
    # UI elements
    'background': '#1a1a1a',
    'background_light': '#222',
    'background_highlight': '#2a2a2a',
    'border': '#333',
    'border_light': '#555',
    'border_active': '#44aa44',
    'text': '#888',
    'text_bright': '#aaa',
    'text_dim': '#555',
    
    # Indicators
    'audio_on': '#44ff44',
    'audio_off': '#555',
    'midi_on': '#ffaa00',
    'midi_off': '#555',
    'clock_pulse': '#44ff44',
    
    # Sliders/controls
    'slider_groove': '#333',
    'slider_handle': '#888',
    'slider_handle_hover': '#aaa',
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
                background-color: #446644;
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
                background-color: #664422;
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
                background-color: #664444;
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
