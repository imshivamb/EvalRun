"""Interval estimates and percentiles for repeated evaluation trials.

Pure functions with no third-party dependencies. Every interval is a two-sided
95% interval; other confidence levels are deliberately not offered so that a
report can never silently mix them.
"""

import math
from typing import List, Optional, Sequence, Tuple

CONFIDENCE_LEVEL = 0.95

# Two-sided 95% normal quantile.
_Z_95 = 1.959963984540054

# Two-sided 95% Student-t critical values by degrees of freedom.
_T_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
    40: 2.021, 60: 2.000, 120: 1.980,
}


def t_critical_95(df: int) -> float:
    """Returns the two-sided 95% Student-t critical value for ``df`` degrees of freedom.

    Between tabulated values the next lower tabulated ``df`` is used, which
    gives a slightly wider (conservative) interval.
    """
    if df < 1:
        raise ValueError("degrees of freedom must be at least 1")
    if df in _T_95:
        return _T_95[df]
    if df > 120:
        return _Z_95
    return _T_95[max(k for k in _T_95 if k <= df)]


def wilson_interval(successes: int, trials: int) -> Optional[Tuple[float, float]]:
    """Wilson score interval for a binomial proportion, as fractions in [0, 1].

    Returns None when there are no trials.
    """
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("successes must be between 0 and trials")
    if trials == 0:
        return None
    z2 = _Z_95 ** 2
    p_hat = successes / trials
    denom = 1 + z2 / trials
    center = (p_hat + z2 / (2 * trials)) / denom
    half = _Z_95 * math.sqrt(p_hat * (1 - p_hat) / trials + z2 / (4 * trials ** 2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("mean of an empty sequence")
    return sum(values) / len(values)


def sample_std(values: Sequence[float]) -> Optional[float]:
    """Sample standard deviation (n - 1). None when fewer than two values."""
    if len(values) < 2:
        return None
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def mean_interval(values: Sequence[float]) -> Optional[Tuple[float, float]]:
    """Student-t interval for the mean. None when fewer than two values."""
    std = sample_std(values)
    if std is None:
        return None
    n = len(values)
    half = t_critical_95(n - 1) * std / math.sqrt(n)
    m = mean(values)
    return m - half, m + half


def percentile(values: Sequence[float], q: float) -> float:
    """Percentile with linear interpolation between closest ranks (``q`` in [0, 100])."""
    if not values:
        raise ValueError("percentile of an empty sequence")
    if not 0 <= q <= 100:
        raise ValueError("q must be between 0 and 100")
    ordered: List[float] = sorted(values)
    position = (len(ordered) - 1) * q / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
