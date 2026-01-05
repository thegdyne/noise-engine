"""
MasterController - Handles master section, EQ, compressor, limiter, audio device, and levels.

Extracted from MainFrame as Phase 4 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

from src.config import OSC_PATHS
from src.gui.theme import COLORS
from src.utils.logger import logger


class MasterController:
    """Handles master section parameters and OSC dispatch."""
    
    def __init__(self, main_frame):
        self.main = main_frame

    def on_master_volume_from_master(self, volume):
        """Handle master volume change from master section."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_volume'], [volume])
        logger.info(f"Master volume: {volume:.2f}", component="OSC")
        self.main._mark_dirty()

    def on_meter_mode_changed(self, mode):
        """Handle meter mode toggle (PRE=0, POST=1)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_meter_toggle'], [mode])
        mode_name = "POST" if mode == 1 else "PRE"
        logger.info(f"Master meter: {mode_name}", component="OSC")
    
    def on_limiter_ceiling_changed(self, db):
        """Handle limiter ceiling change (dB value)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_limiter_ceiling'], [db])
        logger.debug(f"Limiter ceiling: {db:.1f}dB", component="OSC")
    
    def on_limiter_bypass_changed(self, bypass):
        """Handle limiter bypass toggle (0=on, 1=bypassed)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_limiter_bypass'], [bypass])
        state = "BYPASSED" if bypass == 1 else "ON"
        logger.info(f"Limiter: {state}", component="OSC")
    
    # === EQ Handlers ===
    
    def on_eq_lo_changed(self, db):
        """Handle EQ LO change (dB value)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_eq_lo'], [db])
    
    def on_eq_mid_changed(self, db):
        """Handle EQ MID change (dB value)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_eq_mid'], [db])
    
    def on_eq_hi_changed(self, db):
        """Handle EQ HI change (dB value)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_eq_hi'], [db])
    
    def on_eq_lo_kill_changed(self, kill):
        """Handle EQ LO kill toggle."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_eq_lo_kill'], [kill])
        state = "KILLED" if kill == 1 else "OFF"
        logger.info(f"EQ LO Kill: {state}", component="OSC")
    
    def on_eq_mid_kill_changed(self, kill):
        """Handle EQ MID kill toggle."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_eq_mid_kill'], [kill])
        state = "KILLED" if kill == 1 else "OFF"
        logger.info(f"EQ MID Kill: {state}", component="OSC")
    
    def on_eq_hi_kill_changed(self, kill):
        """Handle EQ HI kill toggle."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_eq_hi_kill'], [kill])
        state = "KILLED" if kill == 1 else "OFF"
        logger.info(f"EQ HI Kill: {state}", component="OSC")
    
    def on_eq_locut_changed(self, enabled):
        """Handle EQ lo cut toggle (0=off, 1=on)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_eq_locut'], [enabled])
        state = "ON" if enabled == 1 else "OFF"
        logger.info(f"EQ Lo Cut: {state}", component="OSC")
    
    def on_eq_bypass_changed(self, bypass):
        """Handle EQ bypass toggle (0=on, 1=bypassed)."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_eq_bypass'], [bypass])
        state = "BYPASSED" if bypass == 1 else "ON"
        logger.info(f"EQ: {state}", component="OSC")
    
    # === Compressor Handlers ===
    
    def on_comp_threshold_changed(self, db):
        """Handle compressor threshold change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_comp_threshold'], [db])
    
    def on_comp_ratio_changed(self, idx):
        """Handle compressor ratio change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_comp_ratio'], [idx])
    
    def on_comp_attack_changed(self, idx):
        """Handle compressor attack change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_comp_attack'], [idx])
    
    def on_comp_release_changed(self, idx):
        """Handle compressor release change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_comp_release'], [idx])
    
    def on_comp_makeup_changed(self, db):
        """Handle compressor makeup change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_comp_makeup'], [db])
    
    def on_comp_sc_hpf_changed(self, idx):
        """Handle compressor SC HPF change."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_comp_sc_hpf'], [idx])
    
    def on_comp_bypass_changed(self, bypass):
        """Handle compressor bypass toggle."""
        if self.main.osc_connected:
            self.main.osc.client.send_message(OSC_PATHS['master_comp_bypass'], [bypass])
        state = "BYPASSED" if bypass == 1 else "ON"
        logger.info(f"Compressor: {state}", component="OSC")
    
    def on_comp_gr_received(self, gr_db):
        """Handle compressor GR meter update."""
        self.main.master_section.set_comp_gr(gr_db)
    
    # === Audio Device Handlers ===
    
    def on_audio_device_changed(self, device_name):
        """Handle audio device selection from dropdown - disabled for now."""
        pass
    
    def on_audio_devices_received(self, devices, current):
        """Handle audio device list from SC."""
        logger.info(f"Audio devices: {len(devices)} available, current: {current}", component="OSC")
        self.main.audio_selector.set_devices(devices, current)
    
    def on_audio_device_changing(self, device_name):
        """Handle notification that SC is changing audio device."""
        logger.info(f"Audio device changing to: {device_name}...", component="OSC")
        self.main.status_label.setText("Switching...")
        self.main.status_label.setStyleSheet(f"color: {COLORS['submenu_text']};")
    
    def on_audio_device_ready(self, device_name):
        """Handle notification that SC finished changing device."""
        logger.info(f"Audio device ready: {device_name}", component="OSC")
        self.main.status_label.setText("Connected")
        self.main.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
        self.main.audio_selector.set_enabled(True)
        self.main.osc.query_audio_devices()
    
    # === Level Meters ===
        
    def on_levels_received(self, amp_l, amp_r, peak_l, peak_r):
        """Handle level meter data from SuperCollider."""
        self.main.master_section.set_levels(amp_l, amp_r, peak_l, peak_r)
    
    def on_channel_levels_received(self, slot_id, amp_l, amp_r):
        """Handle per-channel level meter data from SuperCollider."""
        self.main.mixer_panel.set_channel_levels(slot_id, amp_l, amp_r)
