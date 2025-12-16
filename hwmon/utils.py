from math import nan
from typing import Iterable, Sequence


def mean(values: Iterable[float | None]) -> float:
    if not values:
        return nan
    return sum(values) / len(values)


def linear_scale(values: Sequence[float]) -> list[float]:
    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val
    return [(val - min_val) / range_val for val in values]