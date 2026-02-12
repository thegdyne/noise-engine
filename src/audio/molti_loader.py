"""
MOLTI-SAMP loader — loads multisamples into SuperCollider buffers.

Workflow:
    1. Parse .korgmultisample
    2. Resolve sample paths
    3. Allocate bufnums from pool
    4. Load audio files via /b_allocReadChannel
    5. Build + write noteMap and zoneBuf tables
    6. Update bufBus on target slot

All SC communication via direct OSC client (SC server commands).
"""

import time
import wave
from pathlib import Path
from typing import Dict, List, Optional

from src.audio.korg_multisample import (
    MultisampleDef,
    parse_korgmultisample, resolve_sample_paths, build_note_map
)
from src.audio.molti_buf_pool import MoltiBufPool
from src.utils.logger import logger


class MoltiLoader:
    """Loads multisample sets into SC for a specific slot."""

    def __init__(self, sc_client, buf_pool: MoltiBufPool):
        """
        Args:
            sc_client: OSC client with send_message(path, args) method
            buf_pool: Shared buffer number pool
        """
        self.sc = sc_client
        self.pool = buf_pool

    def _sync_wait(self, wait_ms: int = 100):
        """Wait for SC server to complete pending async commands.

        Uses time.sleep as interim solution — the OSC bridge uses
        fire-and-forget messaging with no /sync listener.
        Scale wait time with number of buffers being loaded.
        """
        time.sleep(wait_ms / 1000.0)

    def load(
        self,
        slot: int,
        filepath,
        sample_roots: Optional[List[Path]] = None,
        buf_bus_index: Optional[int] = None
    ) -> Dict:
        """
        Load a multisample into a slot.

        Args:
            slot: Target slot (0-7)
            filepath: Path to .korgmultisample file
            sample_roots: Additional sample search directories
            buf_bus_index: SC control bus index for this slot's bufBus.
                          If None, caller must provide it.

        Returns:
            Dict with load results:
                - name: str (multisample name)
                - zone_count: int
                - mapped_notes: int (how many of 128 notes are mapped)
                - errors: List[str] (non-fatal warnings)

        Raises:
            FileNotFoundError: If multisample or samples not found
            RuntimeError: If buffer pool exhausted
        """
        filepath = Path(filepath)
        logger.info(f"[MOLTI] Loading {filepath.name} into slot {slot}", component="MOLTI")

        # 1. Parse
        msdef = parse_korgmultisample(filepath)
        logger.info(
            f"[MOLTI] Parsed: {msdef.name}, {msdef.zone_count} zones",
            component="MOLTI"
        )

        # 2. Resolve paths
        errors = resolve_sample_paths(msdef, sample_roots)
        if errors:
            raise FileNotFoundError(
                f"Cannot resolve sample paths:\n" +
                "\n".join(errors)
            )

        # 3. Unload previous (if any)
        self.unload(slot, buf_bus_index)

        # 4. Allocate bufnums: 1 noteMapBuf + 1 zoneBufBuf + N audio buffers
        total_bufs = 2 + msdef.zone_count
        bufnums = self.pool.alloc(slot, total_bufs)

        note_map_bufnum = bufnums[0]
        zone_buf_bufnum = bufnums[1]
        audio_bufnums = bufnums[2:]

        # 5. Load audio files
        for i, zone in enumerate(msdef.zones):
            wav_path = str(zone.resolved_path)
            audio_bn = audio_bufnums[i]

            channels = self._detect_channels(wav_path)

            if channels == 1:
                # Mono -> duplicate to stereo: [0, 0]
                self.sc.send_message("/b_allocReadChannel", [
                    audio_bn, wav_path, 0, -1, 0, 0
                ])
            else:
                # Stereo: [0, 1]
                self.sc.send_message("/b_allocReadChannel", [
                    audio_bn, wav_path, 0, -1, 0, 1
                ])

            logger.info(
                f"[MOLTI]   Zone {i}: {zone.wav_path} -> buf {audio_bn} ({channels}ch)",
                component="MOLTI"
            )

        # Wait for all audio loads to complete
        self._sync_wait(max(100, msdef.zone_count * 20))

        # 6. Build tables
        note_map = build_note_map(msdef.zones)
        zone_buf = [audio_bufnums[i] for i in range(msdef.zone_count)]

        # 7. Allocate and write noteMapBuf (128 floats)
        # CRITICAL: values MUST be float — python-osc sends ints as OSC 'i' type,
        # but SC /b_setn expects float sample data. Int bytes misread as float
        # would garble the table (e.g. int 3 → float ≈0.0, mapping all notes to zone 0).
        self.sc.send_message("/b_alloc", [note_map_bufnum, 128, 1])
        self._sync_wait(50)
        self.sc.send_message("/b_setn",
            [note_map_bufnum, 0, 128] + [float(x) for x in note_map])

        # 8. Allocate and write zoneBufBuf (same float requirement)
        self.sc.send_message("/b_alloc", [zone_buf_bufnum, msdef.zone_count, 1])
        self._sync_wait(50)
        self.sc.send_message("/b_setn",
            [zone_buf_bufnum, 0, msdef.zone_count] + [float(x) for x in zone_buf])

        # 9. Update bufBus (atomic — SC reads all 4 channels together)
        if buf_bus_index is not None:
            self.sc.send_message("/c_setn", [
                buf_bus_index, 4,
                note_map_bufnum,
                zone_buf_bufnum,
                msdef.zone_count,
                0  # reserved
            ])
            logger.info(
                f"[MOLTI] bufBus updated @ bus {buf_bus_index}: noteMap={note_map_bufnum}, "
                f"zoneBuf={zone_buf_bufnum}, count={msdef.zone_count}",
                component="MOLTI"
            )

        mapped_notes = sum(1 for n in note_map if n >= 0)
        logger.info(
            f"[MOLTI] Load complete: {msdef.zone_count} zones, "
            f"{mapped_notes}/128 notes mapped",
            component="MOLTI"
        )

        return {
            'name': msdef.name,
            'zone_count': msdef.zone_count,
            'mapped_notes': mapped_notes,
            'errors': [],
        }

    def unload(self, slot: int, buf_bus_index: Optional[int] = None):
        """
        Unload multisample from slot — free buffers, reset bufBus.

        Args:
            slot: Target slot (0-7)
            buf_bus_index: SC control bus index for bufBus reset
        """
        # Reset bufBus to silent FIRST (stop playback)
        if buf_bus_index is not None:
            self.sc.send_message("/c_setn", [
                buf_bus_index, 4, -1, -1, 0, 0
            ])

        # Free SC buffers
        freed = self.pool.free_slot(slot)
        for bn in freed:
            self.sc.send_message("/b_free", [bn])

        if freed:
            logger.info(
                f"[MOLTI] Unloaded slot {slot}: freed {len(freed)} buffers",
                component="MOLTI"
            )

    def _detect_channels(self, wav_path: str) -> int:
        """Detect number of channels in wav file."""
        try:
            with wave.open(wav_path, 'rb') as w:
                return w.getnchannels()
        except Exception:
            return 2  # Assume stereo on error
