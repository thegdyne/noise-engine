"""
MixerController - Handles mixer strip parameter changes and OSC dispatch.

Extracted from MainFrame as Phase 4 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

from src.config import OSC_PATHS
from src.utils.logger import logger


class MixerController:
    """Handles mixer strip parameters and OSC dispatch."""
    
    def __init__(self, main_frame):
        self.main = main_frame

    def on_generator_volume_changed(self, gen_id, volume):
        """Handle generator volume change from mixer."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_volume'], [gen_id, volume])
        logger.debug(f"Gen {gen_id} volume: {volume:.2f}", component="OSC")
        self.main._mark_dirty()

    def on_generator_muted(self, gen_id, muted):
        """Handle generator mute from mixer."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_mute'], [gen_id, 1 if muted else 0])
        logger.debug(f"Gen {gen_id} mute: {muted}", component="OSC")
        
    def on_generator_solo(self, gen_id, solo):
        """Handle generator solo from mixer."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_strip_solo'], [gen_id, 1 if solo else 0])
        logger.debug(f"Gen {gen_id} solo: {solo}", component="OSC")
    
    def on_generator_gain_changed(self, gen_id, gain_db):
        """Handle generator gain stage change from mixer."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_gain'], [gen_id, gain_db])
        logger.debug(f"Gen {gen_id} gain: +{gain_db}dB", component="OSC")
    
    def on_generator_pan_changed(self, gen_id, pan):
        """Handle generator pan change from mixer."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['gen_pan'], [gen_id, pan])
        logger.debug(f"Gen {gen_id} pan: {pan:.2f}", component="OSC")
        self.main._mark_dirty()

    def on_generator_eq_changed(self, gen_id, band, value):
        """Handle generator EQ change from mixer. band: 'lo'/'mid'/'hi', value: 0-2 linear."""
        if self.main.osc_connected:
            osc_path = f"{OSC_PATHS['gen_strip_eq_base']}/{band}"
            self.main.osc.client.send_message(osc_path, [gen_id, value])
        logger.debug(f"Gen {gen_id} EQ {band}: {value:.2f}", component="OSC")
        self.main._mark_dirty()

    def on_generator_fx1_send(self, gen_id, value):
        """Handle generator FX1 send change from mixer. value: 0-1."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['strip_fx1_send'], [gen_id, value])
        logger.debug(f"Gen {gen_id} FX1 send: {value:.2f}", component="OSC")

    def on_generator_fx2_send(self, gen_id, value):
        """Handle generator FX2 send change from mixer. value: 0-1."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['strip_fx2_send'], [gen_id, value])
        logger.debug(f"Gen {gen_id} FX2 send: {value:.2f}", component="OSC")

    def on_generator_fx3_send(self, gen_id, value):
        """Handle generator FX3 send change from mixer. value: 0-1."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['strip_fx3_send'], [gen_id, value])
        logger.debug(f"Gen {gen_id} FX3 send: {value:.2f}", component="OSC")

    def on_generator_fx4_send(self, gen_id, value):
        """Handle generator FX4 send change from mixer. value: 0-1."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['strip_fx4_send'], [gen_id, value])
        logger.debug(f"Gen {gen_id} FX4 send: {value:.2f}", component="OSC")

    # Legacy aliases for backward compatibility
    def on_generator_echo_send(self, gen_id, value):
        """Handle generator echo send change (legacy - routes to FX1)."""
        self.on_generator_fx1_send(gen_id, value)

    def on_generator_verb_send(self, gen_id, value):
        """Handle generator verb send change (legacy - routes to FX2)."""
        self.on_generator_fx2_send(gen_id, value)
