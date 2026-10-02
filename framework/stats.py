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


def welch_interval(
    baseline: Sequence[float], candidate: Sequence[float]
) -> Optional[Tuple[float, float, float]]:
    """Welch interval for mean(candidate) - mean(baseline) from independent samples.

    Returns (difference, low, high), or None when either side has fewer than two
    values. Welch-Satterthwaite degrees of freedom are rounded down, which
    widens the interval slightly (conservative).
    """
    if len(baseline) < 2 or len(candidate) < 2:
        return None
    difference = mean(candidate) - mean(baseline)
    var_b = sample_std(baseline) ** 2 / len(baseline)
    var_c = sample_std(candidate) ** 2 / len(candidate)
    se = math.sqrt(var_b + var_c)
    if se == 0:
        return difference, difference, difference
    df = (var_b + var_c) ** 2 / (
        var_b ** 2 / (len(baseline) - 1) + var_c ** 2 / (len(candidate) - 1)
    )
    half = t_critical_95(max(1, math.floor(df))) * se
    return difference, difference - half, difference + half


# One-sided normal quantile for 80% power.
_Z_80 = 0.8416212335729143
TARGET_POWER = 0.80


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def gate_power(sigma: float, drop: float, threshold: float, trials: int) -> float:
    """Probability that the statistical gate blocks a true drop of ``drop`` points.

    Models the gate rule exactly: block when the Welch interval excludes zero
    and the estimated drop exceeds ``threshold``. Assumes ``trials`` trials per
    side with a common score standard deviation ``sigma`` and a normally
    distributed estimate, so the result is an approximation for small samples.
    """
    if trials < 2:
        raise ValueError("the statistical gate needs at least 2 trials per side")
    if sigma <= 0:
        return 1.0 if drop > threshold else 0.0
    se = sigma * math.sqrt(2 / trials)
    bar = max(threshold, t_critical_95(2 * trials - 2) * se)
    return normal_cdf((drop - bar) / se)


def trials_for_power(
    sigma: float, drop: float, threshold: float, max_trials: int = 1000
) -> Optional[int]:
    """Smallest trials per side at which the gate blocks ``drop`` with 80% probability.

    Returns None when no trial count reaches 80%, which is always the case for
    a drop no larger than ``threshold``.
    """
    if drop <= threshold:
        return None
    for trials in range(2, max_trials + 1):
        if gate_power(sigma, drop, threshold, trials) >= TARGET_POWER:
            return trials
    return None


def minimum_detectable_drop(sigma: float, threshold: float, trials: int) -> float:
    """Smallest true drop the gate blocks with 80% probability at ``trials`` per side."""
    if trials < 2:
        raise ValueError("the statistical gate needs at least 2 trials per side")
    se = sigma * math.sqrt(2 / trials)
    return max(threshold, t_critical_95(2 * trials - 2) * se) + _Z_80 * se


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
