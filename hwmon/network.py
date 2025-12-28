from hwmon.pdh_counters import PDHQuery


class NetworkBackend:
    def __init__(self) -> None:
        self._query = PDHQuery()
        self._query.add_counter(
            "bytes_recv", r"\Network Interface(*)\Bytes Received/sec"
        )
        self._query.add_counter("bytes_sent", r"\Network Interface(*)\Bytes Sent/sec")
        self._keys_cache: list[str] = []

    def sample(self) -> dict[str, float | None]:
        """Collect current network readings (bytes per second)."""
        self._query.collect()
        return {
            "net_in": self._get_total_bytes("bytes_recv"),
            "net_out": self._get_total_bytes("bytes_sent"),
        }

    def _get_total_bytes(self, key: str) -> float | None:
        """Sum bytes across all network interfaces, excluding loopback."""
        readings = self._query.get_dict(key)
        total = 0.0
        has_values = False

        if not self._keys_cache:
            self._keys_cache = [
                name
                for name, value in readings.items()
                if (
                    value is not None
                    and "loopback" not in name
                    and "_total" not in name
                )
            ]

        for name in self._keys_cache:
            if (value := readings.get(name)) is not None:
                total += value
                has_values = True

        return total if has_values else None
