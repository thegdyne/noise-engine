"""
Default Skin - High Contrast

Clean, high-contrast dark theme with clear visual hierarchy.
Designed for readability and accessibility.
"""
import platform

SKIN = {
    # ==========================================================================
    # PALETTE - Base colours everything derives from
    # ==========================================================================
    
    # Backgrounds (darkest to lightest)
    'bg_darkest': '#000000',
    'bg_dark': '#0d0d0d',
    'bg_base': '#141414',
    'bg_mid': '#1a1a1a',
    'bg_light': '#242424',
    'bg_highlight': '#2e2e2e',
    
    # Borders
    'border_dark': '#2a2a2a',
    'border_mid': '#3a3a3a',
    'border_light': '#4a4a4a',
    'border_bright': '#666666',
    
    # Text (dimmest to brightest)
    'text_dim': '#606060',
    'text_mid': '#909090',
    'text_normal': '#b0b0b0',
    'text_bright': '#d0d0d0',
    'text_white': '#f0f0f0',
    
    # ==========================================================================
    # ACCENTS - Module type colours
    # ==========================================================================
    
    # Generators - Green
    'accent_generator': '#00ff66',
    'accent_generator_dim': '#00aa44',
    'accent_generator_bg': '#0a2a15',
    
    # Mod LFO - Cyan/Blue
    'accent_mod_lfo': '#00ccff',
    'accent_mod_lfo_dim': '#0088aa',
    'accent_mod_lfo_bg': '#0a1a25',
    
    # Mod Sloth - Orange
    'accent_mod_sloth': '#ff8800',
    'accent_mod_sloth_dim': '#aa5500',
    'accent_mod_sloth_bg': '#251a0a',
    
    # Effects - Purple
    'accent_effect': '#aa88ff',
    'accent_effect_dim': '#6644aa',
    'accent_effect_bg': '#1a1525',
    
    # Master - White/Silver
    'accent_master': '#ffffff',
    'accent_master_dim': '#aaaaaa',
    'accent_master_bg': '#1a1a1a',
    
    # ==========================================================================
    # STATES - Interactive element states
    # ==========================================================================
    
    # Enabled/Active (green)
    'state_enabled_bg': '#0a2a15',
    'state_enabled_text': '#00ff66',
    'state_enabled_border': '#00aa44',
    'state_enabled_hover': '#0d3a1d',
    
    # Disabled/Off
    'state_disabled_bg': '#1a1a1a',
    'state_disabled_text': '#505050',
    'state_disabled_border': '#2a2a2a',
    
    # Selected (blue)
    'state_selected_bg': '#0a1525',
    'state_selected_text': '#88aaff',
    'state_selected_border': '#4466aa',
    
    # Warning (red)
    'state_warning_bg': '#2a0a0a',
    'state_warning_text': '#ff6666',
    'state_warning_border': '#aa4444',
    'state_warning_hover': '#3a1515',
    
    # Submenu/Secondary (orange)
    'state_submenu_bg': '#251a0a',
    'state_submenu_text': '#ff8800',
    'state_submenu_border': '#aa5500',
    'state_submenu_hover': '#302010',
    
    # ==========================================================================
    # INDICATORS - LEDs, meters, status
    # ==========================================================================
    
    # Gate LED
    'led_gate_on': '#00ff66',
    'led_gate_off': '#0a2a15',
    'led_gate_border_on': '#00aa44',
    'led_gate_border_off': '#1a3a25',
    
    # Mute
    'led_mute_on': '#ff3333',
    'led_mute_on_text': '#ffffff',
    'led_mute_off': '#2a1515',
    'led_mute_off_text': '#884444',
    
    # Audio indicator
    'led_audio_on': '#00ff66',
    'led_audio_off': '#303030',
    
    # MIDI indicator  
    'led_midi_on': '#ffaa00',
    'led_midi_off': '#303030',
    
    # Clock pulse
    'led_clock': '#00ff66',
    
    # Meters
    'meter_bg': '#0a0a0a',
    'meter_normal': '#00cc44',
    'meter_warn': '#ffaa00',
    'meter_clip': '#ff3333',
    
    # ==========================================================================
    # CONTROLS - Sliders, knobs, buttons
    # ==========================================================================
    
    # Sliders
    'slider_groove': '#1a1a1a',
    'slider_groove_border': '#3a3a3a',
    'slider_handle': '#808080',
    'slider_handle_hover': '#a0a0a0',
    'slider_handle_border': '#4a4a4a',
    
    # MIDI channel button
    'midi_ch_bg': '#0a1525',
    'midi_ch_text': '#88aaff',
    'midi_ch_off_bg': '#141414',
    'midi_ch_off_text': '#404040',
    
    # ==========================================================================
    # SPECIAL
    # ==========================================================================
    
    # BPM display
    'bpm_text': '#ff3333',
    
    # WIP panels (greyed out)
    'wip_bg': '#0d0d0d',
    'wip_bg_light': '#141414',
    'wip_border': '#1a1a1a',
    'wip_text': '#2a2a2a',
    'wip_text_dim': '#202020',
    
    # Scope traces
    'scope_trace_a': '#00ff66',
    'scope_trace_b': '#00ccff', 
    'scope_trace_c': '#ff8800',
    'scope_trace_d': '#ff00ff',  # Magenta for D/R output
    'scope_grid': '#2a2a2a',
    'scope_center': '#3a3a3a',
    
    # ==========================================================================
    # FONTS
    # ==========================================================================
    
    'font_family': 'Helvetica',
    'font_mono': 'Menlo' if platform.system() == 'Darwin' else 'Consolas',
    
    # Font sizes
    'font_size_display': 32,
    'font_size_title': 16,
    'font_size_section': 12,
    'font_size_slot_title': 11,
    'font_size_label': 10,
    'font_size_small': 9,
    'font_size_tiny': 8,
    'font_size_micro': 7,
    
    # ==========================================================================
    # INTERACTION
    # ==========================================================================
    
    'drag_slider_normal': 100,
    'drag_slider_fine': 400,
    'drag_cycle_normal': 15,
    'drag_cycle_fine': 40,
    'drag_generator_normal': 5,
    'drag_generator_fine': 12,
    'drag_bpm_normal': 3,
    'drag_bpm_fine': 35,
}
