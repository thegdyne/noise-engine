"""
Preset utilities for R1.1 Preset Browser.

Contains:
- TimestampProvider: monotonic timestamp generation
- canonical_path: deterministic path canonicalization
- RecentPresetEntry: recents data model
- RecentsManager: recents persistence and management
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List
import json
import os
import sys
import unicodedata
import threading


# =============================================================================
# TIMESTAMP PROVIDER
# =============================================================================

class TimestampProvider:
    """
    Generates monotonically increasing timestamps per R1.1 spec.

    Guarantees:
    - Strictly increasing timestamps within a session
    - ISO 8601 format with UTC timezone and millisecond precision
    - Handles wall clock going backward (adds 1ms to last_timestamp)
    """

    _instance: Optional['TimestampProvider'] = None
    _lock = threading.Lock()

    def __init__(self):
        # Initialize last_timestamp to current wall clock
        self._last_timestamp = self._wall_clock_now()
        self._last_dt = self._parse_timestamp(self._last_timestamp)

    @classmethod
    def get_instance(cls) -> 'TimestampProvider':
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def now(cls) -> str:
        """Generate next monotonic timestamp."""
        return cls.get_instance()._generate()

    def _generate(self) -> str:
        """
        Generate next timestamp per spec algorithm:
        1. t = wall_clock_now_formatted
        2. If t <= last_timestamp: return (last_timestamp + 1ms)
        3. Otherwise return t
        4. Update last_timestamp
        """
        with self._lock:
            t = self._wall_clock_now()
            t_dt = self._parse_timestamp(t)

            if t_dt <= self._last_dt:
                # Clock went backward or same millisecond - add 1ms
                self._last_dt = self._last_dt + timedelta(milliseconds=1)
            else:
                self._last_dt = t_dt

            self._last_timestamp = self._format_timestamp(self._last_dt)
            return self._last_timestamp

    def _wall_clock_now(self) -> str:
        """Get current wall clock time as ISO 8601 string with ms precision."""
        return self._format_timestamp(datetime.now(timezone.utc))

    def _format_timestamp(self, dt: datetime) -> str:
        """Format datetime as ISO 8601 with ms precision and Z timezone."""
        # Format: 2025-01-23T12:34:56.789Z
        return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{dt.microsecond // 1000:03d}Z'

    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse ISO 8601 timestamp string to datetime."""
        # Handle Z suffix
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            # Fallback for malformed timestamps
            return datetime.now(timezone.utc)


# =============================================================================
# CANONICAL PATH
# =============================================================================

def canonical_path(path_like: str) -> str:
    """
    Compute canonical path per R1.1 spec.

    Algorithm (strict order):
    1. abs = os.path.abspath(os.path.expanduser(p))
    2. real = os.path.normpath(os.path.realpath(abs))
    3. nfc = unicodedata.normalize("NFC", real)
    4. Case normalization (platform-specific):
       - Windows: canon = nfc.lower()
       - macOS/Linux: canon = nfc (case preserved)

    Properties:
    - Idempotent: canonical_path(canonical_path(p)) == canonical_path(p)
    - Deterministic: same input always produces same output
    """
    # Step 1: Expand user and make absolute
    abs_path = os.path.abspath(os.path.expanduser(path_like))

    # Step 2: Resolve symlinks and normalize
    real_path = os.path.normpath(os.path.realpath(abs_path))

    # Step 3: Unicode NFC normalization (string-level only)
    nfc_path = unicodedata.normalize("NFC", real_path)

    # Step 4: Platform-specific case normalization
    if sys.platform == "win32":
        # Windows: case-insensitive filesystem, normalize to lowercase
        canon = nfc_path.lower()
    else:
        # macOS/Linux: preserve case (conservative for case-sensitive volumes)
        canon = nfc_path

    return canon


# =============================================================================
# RECENTS MANAGEMENT
# =============================================================================

MAX_RECENT = 20


@dataclass
class RecentPresetEntry:
    """Entry in the recents list."""
    path: str        # Canonical path string
    name: str        # Display name snapshot
    last_used: str   # ISO 8601 timestamp


class RecentsManager:
    """
    Manages the recents list for the preset browser.

    Recents are stored in:
    - Unix/macOS: ~/.config/noise-engine/recents.json
    - Windows: %APPDATA%/noise-engine/recents.json
    """

    def __init__(self):
        self._recents_path = self._get_recents_path()
        self._failed_placeholder_deletions: set = set()  # Per-session tracking

    def _get_recents_path(self) -> Path:
        """Get platform-specific recents file path."""
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", "~"))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
        return base.expanduser() / "noise-engine" / "recents.json"

    def load(self) -> List[RecentPresetEntry]:
        """
        Load and deduplicate recents from disk.

        Per spec:
        - Missing file: return empty
        - Corrupted file: return empty
        - Deduplicate by canonical path using winner rules
        """
        if not self._recents_path.exists():
            return []

        try:
            with open(self._recents_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(data, list):
            return []

        # Load entries with load_index
        indexed_entries = []
        for load_index, entry in enumerate(data):
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "")
            name = entry.get("name", "")
            last_used = entry.get("last_used", "")
            if path:
                indexed_entries.append((load_index, path, name, last_used))

        # Deduplicate by canonical path
        deduped = self._deduplicate(indexed_entries)

        # Sort: last_used descending, name ascending (case-insensitive), path ascending
        deduped.sort(key=lambda e: (
            self._sort_key_last_used(e.last_used),
            unicodedata.normalize("NFC", e.name).casefold(),
            e.path
        ))

        return deduped

    def _deduplicate(self, indexed_entries: List[tuple]) -> List[RecentPresetEntry]:
        """
        Deduplicate entries by canonical path.

        Winner rules (in order):
        1. Parseable last_used over unparseable
        2. Maximum last_used instant
        3. Smallest name (case-insensitive)
        4. Smallest stored path (codepoint order)
        5. Smallest load_index (first in file)
        """
        # Group by canonical path
        groups = {}
        for load_index, path, name, last_used in indexed_entries:
            canon = canonical_path(path)
            if canon not in groups:
                groups[canon] = []
            groups[canon].append((load_index, path, name, last_used))

        # Pick winner for each group
        winners = []
        for canon, entries in groups.items():
            # Sort by winner rules
            def winner_key(e):
                load_index, path, name, last_used = e
                parseable = self._is_parseable_timestamp(last_used)
                parsed_dt = self._parse_timestamp_for_sort(last_used) if parseable else datetime.min.replace(tzinfo=timezone.utc)
                name_norm = unicodedata.normalize("NFC", name).casefold()
                return (
                    not parseable,  # Parseable first (False < True)
                    -parsed_dt.timestamp() if parseable else 0,  # Max last_used first
                    name_norm,  # Smallest name
                    path,  # Smallest path
                    load_index  # First in file
                )

            entries.sort(key=winner_key)
            _, _, name, last_used = entries[0]
            winners.append(RecentPresetEntry(path=canon, name=name, last_used=last_used))

        return winners

    def _is_parseable_timestamp(self, ts: str) -> bool:
        """Check if timestamp is parseable."""
        try:
            self._parse_timestamp_for_sort(ts)
            return True
        except (ValueError, TypeError):
            return False

    def _parse_timestamp_for_sort(self, ts: str) -> datetime:
        """Parse timestamp for sorting purposes."""
        if not ts:
            raise ValueError("Empty timestamp")
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        return datetime.fromisoformat(ts)

    def _sort_key_last_used(self, ts: str) -> tuple:
        """
        Generate sort key for last_used (descending).
        Unparseable timestamps sort last.
        """
        try:
            dt = self._parse_timestamp_for_sort(ts)
            return (0, -dt.timestamp())  # Parseable, negative for descending
        except (ValueError, TypeError):
            return (1, 0)  # Unparseable last

    def record_use(self, path_like: str, display_name: str, last_used_timestamp: str) -> bool:
        """
        Record a preset use in recents.

        Per spec:
        - Canonicalize path
        - Load and deduplicate existing
        - Upsert entry
        - Cap to MAX_RECENT
        - Persist atomically

        Args:
            path_like: Path to preset file
            display_name: Display name snapshot
            last_used_timestamp: Timestamp from operation context (not generated here)

        Returns:
            True if successful, False if persistence failed
        """
        canon = canonical_path(path_like)

        # Load existing
        recents = self.load()

        # Remove existing entry for this path if present
        recents = [e for e in recents if e.path != canon]

        # Add new entry at front
        new_entry = RecentPresetEntry(
            path=canon,
            name=display_name,
            last_used=last_used_timestamp
        )
        recents.insert(0, new_entry)

        # Cap to MAX_RECENT
        recents = recents[:MAX_RECENT]

        # Persist
        return self._save(recents)

    def remove(self, path_like: str) -> bool:
        """
        Remove a preset from recents.

        Returns:
            True if successful, False if persistence failed
        """
        canon = canonical_path(path_like)
        recents = self.load()
        recents = [e for e in recents if e.path != canon]
        return self._save(recents)

    def _save(self, recents: List[RecentPresetEntry]) -> bool:
        """
        Save recents to disk atomically.

        Per spec: write temp file in same directory, then os.replace
        """
        # Ensure directory exists
        self._recents_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize
        data = [
            {"path": e.path, "name": e.name, "last_used": e.last_used}
            for e in recents
        ]
        json_str = json.dumps(data, indent=2)

        # Atomic write
        temp_path = self._recents_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            os.replace(temp_path, self._recents_path)
            return True
        except OSError:
            # Clean up temp file if possible
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def get_failed_placeholder_deletions(self) -> set:
        """Get the set of paths that failed placeholder deletion this session."""
        return self._failed_placeholder_deletions

    def mark_placeholder_deletion_failed(self, path: str):
        """Mark a path as having failed placeholder deletion."""
        self._failed_placeholder_deletions.add(canonical_path(path))

    def has_placeholder_deletion_failed(self, path: str) -> bool:
        """Check if a path has already failed placeholder deletion this session."""
        return canonical_path(path) in self._failed_placeholder_deletions


# Singleton instance
_recents_manager: Optional[RecentsManager] = None


def get_recents_manager() -> RecentsManager:
    """Get singleton RecentsManager instance."""
    global _recents_manager
    if _recents_manager is None:
        _recents_manager = RecentsManager()
    return _recents_manager
