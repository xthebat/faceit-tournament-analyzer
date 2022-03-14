from typing import Iterable


def mean(iterable: Iterable):
    items = list(iterable)
    return sum(items) / len(items)


def percent(a, b) -> float:
    return float(a) / float(b) * 100.0
