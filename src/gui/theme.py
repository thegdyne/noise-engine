"""
Theme - Centralized color and style definitions
All UI components reference this for consistent styling

Loads from active skin in src/gui/skins/
RULE: All sliders must be vertical - no horizontal sliders
"""
from .skins import active as skin

# =============================================================================
# SKIN ACCESS
# =============================================================================

def get(key, default='#ff00ff'):
    """Get value from active skin. Magenta = missing key."""
    return skin.SKIN.get(key, default)

def accent(module_type):
    """Get accent colour for module type: 'generator', 'mod_lfo', 'mod_sloth', 'effect', 'master'."""
    return get(f'accent_{module_type}')

def accent_dim(module_type):
    """Get dimmed accent colour for module type."""
    return get(f'accent_{module_type}_dim')

def accent_bg(module_type):
    """Get background accent colour for module type."""
    return get(f'accent_{module_type}_bg')

# =============================================================================
# BACKWARDS COMPATIBLE EXPORTS
# These map old COLORS keys to new skin keys
# =============================================================================

FONT_FAMILY = get('font_family')
MONO_FONT = get('font_mono')

FONT_SIZES = {
    'display': get('font_size_display'),
    'title': get('font_size_title'),
    'section': get('font_size_section'),
    'slot_title': get('font_size_slot_title'),
    'label': get('font_size_label'),
    'small': get('font_size_small'),
    'tiny': get('font_size_tiny'),
    'micro': get('font_size_micro'),
}

DRAG_SENSITIVITY = {
    'slider_normal': get('drag_slider_normal'),
    'slider_fine': get('drag_slider_fine'),
    'cycle_normal': get('drag_cycle_normal'),
    'cycle_fine': get('drag_cycle_fine'),
    'generator_normal': get('drag_generator_normal'),
    'generator_fine': get('drag_generator_fine'),
    'bpm_value_normal': get('drag_bpm_normal'),
    'bpm_value_fine': get('drag_bpm_fine'),
}

# Main COLORS dict - maps old keys to skin values
COLORS = {
    # States (old naming)
    'enabled': get('state_enabled_bg'),
    'enabled_text': get('state_enabled_text'),
    'enabled_hover': get('state_enabled_hover'),
    'disabled': get('state_disabled_bg'),
    'disabled_text': get('state_disabled_text'),
    'inactive': get('bg_dark'),
    'inactive_text': get('text_dim'),
    
    # Semantic colors
    'active': get('state_enabled_bg'),
    'active_text': get('state_enabled_text'),
    'active_bg': get('state_enabled_bg'),
    'submenu': get('state_submenu_bg'),
    'submenu_text': get('state_submenu_text'),
    'submenu_hover': get('state_submenu_hover'),
    'selected': get('state_selected_bg'),
    'selected_text': get('state_selected_text'),
    'warning': get('state_warning_bg'),
    'warning_text': get('state_warning_text'),
    'warning_hover': get('state_warning_hover'),
    
    # UI elements
    'background': get('bg_mid'),
    'background_dark': get('bg_dark'),
    'background_light': get('bg_light'),
    'background_highlight': get('bg_highlight'),
    'border': get('border_dark'),
    'border_light': get('border_light'),
    'border_active': get('state_enabled_border'),
    'text': get('text_mid'),
    'text_bright': get('text_bright'),
    'text_dim': get('text_dim'),
    'text_label': get('text_dim'),
    
    # Special displays
    'bpm_text': get('bpm_text'),
    
    # Indicators
    'audio_on': get('led_audio_on'),
    'audio_off': get('led_audio_off'),
    'midi_on': get('led_midi_on'),
    'midi_off': get('led_midi_off'),
    'clock_pulse': get('led_clock'),
    
    # Generator controls
    'mute_on': get('led_mute_on'),
    'mute_on_text': get('led_mute_on_text'),
    'mute_off': get('led_mute_off'),
    'mute_off_text': get('led_mute_off_text'),
    'gate_on': get('led_gate_on'),
    'gate_off': get('led_gate_off'),
    'midi_ch_bg': get('midi_ch_bg'),
    'midi_ch_text': get('midi_ch_text'),
    'midi_ch_off_bg': get('midi_ch_off_bg'),
    'midi_ch_off_text': get('midi_ch_off_text'),
    
    # Sliders/controls
    'slider_groove': get('slider_groove'),
    'slider_handle': get('slider_handle'),
    'slider_handle_hover': get('slider_handle_hover'),
    
    # WIP panels
    'wip_bg': get('wip_bg'),
    'wip_bg_light': get('wip_bg_light'),
    'wip_border': get('wip_border'),
    'wip_text': get('wip_text'),
    'wip_text_dim': get('wip_text_dim'),
    
    # === NEW: Module accents ===
    'accent_generator': get('accent_generator'),
    'accent_generator_dim': get('accent_generator_dim'),
    'accent_mod_lfo': get('accent_mod_lfo'),
    'accent_mod_lfo_dim': get('accent_mod_lfo_dim'),
    'accent_mod_sloth': get('accent_mod_sloth'),
    'accent_mod_sloth_dim': get('accent_mod_sloth_dim'),
    'accent_effect': get('accent_effect'),
    'accent_effect_dim': get('accent_effect_dim'),
    
    # Scope
    'scope_trace_a': get('scope_trace_a'),
    'scope_trace_b': get('scope_trace_b'),
    'scope_trace_c': get('scope_trace_c'),
    'scope_grid': get('scope_grid'),
    'scope_center': get('scope_center'),
    
    # Meters
    'meter_bg': get('meter_bg'),
    'meter_normal': get('meter_normal'),
    'meter_warn': get('meter_warn'),
    'meter_clip': get('meter_clip'),
}

# Component-specific overrides (for future use)
COMPONENT_COLORS = {}


def get_color(key, component=None):
    """Get color by key, with optional component-specific override."""
    if component:
        component_key = f"{component}.{key}"
        if component_key in COMPONENT_COLORS:
            return COMPONENT_COLORS[component_key]
    return COLORS.get(key, '#ff00ff')


# =============================================================================
# STYLE FUNCTIONS
# =============================================================================

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
        QSlider {{
            border: none;
            background: transparent;
        }}
        QSlider::groove:vertical {{
            border: 1px solid {get('slider_groove_border')};
            width: 8px;
            background: {COLORS['slider_groove']};
            border-radius: 4px;
        }}
        QSlider::handle:vertical {{
            background: {COLORS['slider_handle']};
            border: 1px solid {get('slider_handle_border')};
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
    """
    return f"""
        QSlider {{
            border: none;
            background: transparent;
        }}
        QSlider::groove:vertical {{
            border: 1px solid {get('slider_groove_border')};
            width: 8px;
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 {COLORS['slider_groove']},
                stop:0.48 {COLORS['slider_groove']},
                stop:0.49 {get('border_light')},
                stop:0.51 {get('border_light')},
                stop:0.52 {COLORS['slider_groove']},
                stop:1 {COLORS['slider_groove']}
            );
            border-radius: 4px;
        }}
        QSlider::handle:vertical {{
            background: {COLORS['slider_handle']};
            border: 1px solid {get('slider_handle_border')};
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
                stop:0 {get('bg_darkest')},
                stop:0.48 {get('bg_darkest')},
                stop:0.49 {get('border_light')},
                stop:0.51 {get('border_light')},
                stop:0.52 {get('bg_darkest')},
                stop:1 {get('bg_darkest')}
            );
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            width: 8px;
            height: 12px;
            margin: -4px 0;
            background: {get('text_dim')};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {get('text_mid')};
        }}
    """


# =============================================================================
# SKINNABLE CONTROL STYLES
# =============================================================================

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
                background-color: {get('state_warning_bg')};
            }}
        """


def gate_indicator_style(active=False):
    """Gate LED indicator - flashes green on triggers."""
    if active:
        return f"""
            QLabel {{
                background-color: {COLORS['gate_on']};
                border-radius: 4px;
                border: 1px solid {get('led_gate_border_on')};
            }}
        """
    else:
        return f"""
            QLabel {{
                background-color: {COLORS['gate_off']};
                border-radius: 4px;
                border: 1px solid {get('led_gate_border_off')};
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
                background-color: {get('state_selected_bg')};
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
            background-color: {get('state_submenu_bg')};
            color: {get('accent_mod_sloth_dim')};
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 10px;
            font-weight: bold;
        }}
    """


# =============================================================================
# PANEL STYLES
# =============================================================================

def panel_style():
    """Standard panel/pane style with border. Use setToolTip() for hover labels."""
    return f"""
        QFrame, QWidget {{
            background-color: {COLORS['background']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
        }}
        QLabel {{
            border: none;
            background: transparent;
        }}
        QPushButton {{
            border: 1px solid {COLORS['border']};
        }}
    """


def panel_style_dark():
    """Darker panel variant for nested sections."""
    return f"""
        QFrame, QWidget {{
            background-color: {COLORS['background_dark']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
        }}
        QLabel {{
            border: none;
            background: transparent;
        }}
    """


def panel_style_highlight():
    """Highlighted panel for active/important sections."""
    return f"""
        QFrame, QWidget {{
            background-color: {COLORS['background_highlight']};
            border: 1px solid {get('border_light')};
            border-radius: 4px;
        }}
        QLabel {{
            border: none;
            background: transparent;
        }}
    """


# Panel tooltips
PANEL_TOOLTIPS = {
    'master': 'MASTER OUTPUT',
    'mixer': 'MIXER - 8 Channel Strips',
    'generators': 'GENERATORS - 8 Synth Slots',
    'mod_sources': 'MODULATION SOURCES - LFOs & Envelopes',
    'fx_chain': 'FX CHAIN - 4 Effect Slots',
    'eq': 'DJ Isolator EQ - 3-band with kill switches',
    'comp': 'SSL G-Series Style Bus Compressor',
    'limiter': 'Brickwall Limiter - Output protection',
    'output': 'Master Output - Volume & Metering',
    'gen_params': 'Generator Parameters',
    'gen_filter': 'Multimode Filter (LP/BP/HP)',
    'gen_env': 'Clock-synced Envelope',
    'fx_delay': 'Delay Effect',
    'fx_reverb': 'Reverb Effect',
    'fx_chorus': 'Chorus Effect',
    'fx_filter': 'Filter Effect',
}


def get_panel_tooltip(key):
    """Get tooltip text for a panel by key."""
    return PANEL_TOOLTIPS.get(key, '')


# =============================================================================
# GENERATOR THEME
# =============================================================================

GENERATOR_THEME = {
    # Param labels
    'param_label_font': MONO_FONT,
    'param_label_size': FONT_SIZES['tiny'],
    'param_label_bold': True,
    'param_label_height': 14,
    'param_label_color': get('text_mid'),
    'param_label_color_dim': get('text_dim'),
    'param_label_color_active': get('accent_generator'),
    
    # Slot (outer container)
    'slot_background': get('bg_mid'),
    'slot_border': get('border_dark'),
    'slot_border_active': get('accent_generator_dim'),
    'slot_margin': (2, 4, 2, 4),  # tighter margins
    
    # Header layout
    'header_inset_left': 14,       # left margin for GEN label
    'header_inset_right': 6,      # right margin - gives breathing room
    'header_selector_text_pad': 2, # internal text padding for selector
    'header_overlay_height': 24,  # reserved space at top of content for header overlay
    'header_frame_gap': 8,        # vertical gap between header and frame (legacy, now unused)
    'header_content_gap': 2,      # header-to-sliders distance inside the frame
    
    # Header
    'header_spacing': 4,
    'header_type_width': 40,      # matches button_strip_width
    'header_type_height': 20,     # shorter height
    
    # GeneratorFrame (inner container for sliders + buttons)
    'frame_background': get('bg_base'),
    'frame_border': get('border_mid'),
    'frame_border_width': 1,
    'frame_border_radius': 4,
    'frame_padding': (3, 3, 3, 3),  # tighter padding
    
    # Slider section
    'slider_column_width': 22,    # width of each label+slider column
    'slider_gap': 1,              # horizontal gap between columns
    'slider_section_spacing': 6, # vertical gap between custom row + standard row
    'slider_min_height': 38,      # minimum slider height (smaller = more compact)
    'content_row_spacing': 2,     # gap between slider section and button strip
    
    # Button strip - order defines visual stacking (top to bottom)
    'button_strip_order': ['filter', 'env', 'rate', 'midi', 'mute', 'gate'],
    'button_strip_width': 40,
    'button_strip_spacing': 2,
    
    # Button strip - per-button config
    'button_strip': {
        'filter': {
            'font': MONO_FONT,
            'font_size': FONT_SIZES['small'],
            'font_bold': True,
            'style': 'enabled',
            'tooltip': 'Filter Type: LP / HP / BP',
            'width': 36,
            'height': 24,
        },
        'env': {
            'font': MONO_FONT,
            'font_size': FONT_SIZES['tiny'],
            'font_bold': True,
            'style': 'disabled',
            'tooltip': 'Envelope source: OFF (drone), CLK (clock), MIDI',
            'width': 36,
            'height': 24,
        },
        'rate': {
            'font': MONO_FONT,
            'font_size': FONT_SIZES['tiny'],
            'font_bold': False,
            'style': 'inactive',
            'tooltip': 'Clock rate\n↑ faster: x8, x4, x2\n↓ slower: /2, /4, /8, /16',
            'width': 36,
            'height': 24,
        },
        'midi': {
            'font': MONO_FONT,
            'font_size': FONT_SIZES['tiny'],
            'font_bold': True,
            'style': 'midi',
            'tooltip': 'MIDI Input Channel (OFF or 1-16)',
            'width': 36,
            'height': 24,
        },
        'mute': {
            'font': MONO_FONT,
            'font_size': FONT_SIZES['small'],
            'font_bold': True,
            'style': 'mute',
            'tooltip': 'Mute Generator',
            'width': 36,
            'height': 20,
        },
        'gate': {
            'style': 'gate',
            'tooltip': 'Gate Activity',
            'width': 36,
            'height': 20,
        },
    },
}


def get_generator_theme(generator_name=None):
    """Get theme dict for a generator, with defaults."""
    theme = GENERATOR_THEME.copy()
    return theme


# =============================================================================
# MODULATOR THEME
# =============================================================================

MODULATOR_THEME = {
    # Slot styling
    'slot_border': get('border_dark'),
    'slot_border_lfo': get('accent_mod_lfo'),
    'slot_border_sloth': get('accent_mod_sloth'),
    'slot_background': get('background_light'),
    'slot_background_empty': get('background'),
    
    # Header
    'header_font': FONT_FAMILY,
    'header_size': FONT_SIZES['small'],
    'header_bold': True,
    'header_color': get('text_bright'),
    'header_spacing': 6,
    'header_button_width': 60,
    'header_button_height': 22,
    
    # Param labels
    'param_label_font': MONO_FONT,
    'param_label_size': FONT_SIZES['micro'],
    'param_label_color': get('text'),
    'param_label_height': 14,
    
    # Param columns / spacing
    'slider_column_width': 26,
    'slider_row_spacing': 8,          # horizontal gap between columns
    'slider_section_margins': (0, 4, 0, 4),
    
    # Output labels
    'output_label_font': MONO_FONT,
    'output_label_size': FONT_SIZES['small'],
    'output_label_bold': True,
    'output_label_color': get('text_bright'),
    'output_label_width': 20,
    
    # Scope
    'scope_height': 50,
    'scope_border': get('border'),
}


def get_modulator_theme(generator_name=None):
    """Get theme dict for a modulator, with defaults."""
    theme = MODULATOR_THEME.copy()
    return theme
