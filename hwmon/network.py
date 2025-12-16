"""Network sensor backend for monitoring network traffic."""

from __future__ import annotations

import time

from hwmon.pdh_counters import PDHQuery


class NetworkBackend:
    """Backend for reading network traffic metrics via PDH counters."""
    
    def __init__(self) -> None:
        self._query = PDHQuery()
        self._query.add_counter("bytes_recv", r"\Network Interface(*)\Bytes Received/sec")
        self._query.add_counter("bytes_sent", r"\Network Interface(*)\Bytes Sent/sec")
        
        # Initialize with first collection
        if self._query.collect():
            time.sleep(0.1)
            self._query.collect()
    
    def sample(self) -> dict[str, float | None]:
        """Collect current network readings (bytes per second)."""
        self._query.collect()
        return {
            "net_in": self._get_total_bytes("bytes_recv"),
            "net_out": self._get_total_bytes("bytes_sent"),
        }
    
    def _get_total_bytes(self, key: str) -> float | None:
        """Sum bytes across all network interfaces, excluding loopback."""
        readings = self._query.get_array(key)
        total = 0.0
        count = 0
        
        for name, value in readings:
            if value is None:
                continue
            label = (name or "").lower()
            # Skip loopback and total aggregates
            if "loopback" in label or "_total" in label:
                continue
            total += value
            count += 1
        
        return total if count > 0 else None

