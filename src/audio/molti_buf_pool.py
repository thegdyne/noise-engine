"""
MOLTI-SAMP buffer number pool manager.

Manages a reserved range of SuperCollider buffer numbers to avoid
collisions with other Noise Engine buffer allocations.

Allocation strategy:
    MOLTI_BUF_BASE = 4000
    MOLTI_BUF_COUNT = 512
    Pool: [4000, 4001, ..., 4511]

Each slot tracks its own allocations for cleanup on unload.
"""

import threading
from typing import Dict, List, Set

from src.utils.logger import logger

MOLTI_BUF_BASE = 4000
MOLTI_BUF_COUNT = 512


class MoltiBufPool:
    """Thread-safe buffer number allocator for MOLTI-SAMP."""

    def __init__(self, base: int = MOLTI_BUF_BASE, count: int = MOLTI_BUF_COUNT):
        self._lock = threading.Lock()
        self._free: List[int] = list(range(base, base + count))
        self._slot_allocs: Dict[int, Set[int]] = {i: set() for i in range(8)}

    def alloc(self, slot: int, count: int = 1) -> List[int]:
        """
        Allocate buffer numbers for a slot.

        Args:
            slot: Generator slot (0-7)
            count: Number of bufnums to allocate

        Returns:
            List of allocated bufnums

        Raises:
            RuntimeError: If pool exhausted
        """
        with self._lock:
            if len(self._free) < count:
                raise RuntimeError(
                    f"MOLTI-SAMP buffer pool exhausted: need {count}, "
                    f"have {len(self._free)} free"
                )
            allocated = self._free[:count]
            self._free = self._free[count:]
            self._slot_allocs[slot].update(allocated)
            return allocated

    def free_slot(self, slot: int) -> List[int]:
        """
        Free all bufnums allocated to a slot.

        Returns:
            List of freed bufnums (for SC /b_free commands)
        """
        with self._lock:
            freed = list(self._slot_allocs[slot])
            self._free.extend(freed)
            self._slot_allocs[slot].clear()
            return freed

    @property
    def available(self) -> int:
        with self._lock:
            return len(self._free)
