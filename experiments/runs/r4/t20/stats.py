"""Small descriptive-statistics helpers used by the reporting pipeline."""


def mean(values):
    total = 0
    for v in values:
        total += v
    return total / len(values)


def median(values):
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def mode(values):
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    best = None
    best_count = 0
    for v, c in counts.items():
        if c > best_count or (c == best_count and v < best):
            best = v
            best_count = c
    return best


def variance(values):
    m = mean(values)
    total = 0
    for v in values:
        total += (v - m) ** 2
    return total / len(values)


def summary(values):
    return {
        "mean": mean(values),
        "median": median(values),
        "mode": mode(values),
        "variance": variance(values),
    }
