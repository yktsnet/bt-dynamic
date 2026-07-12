"""9-cell regime classification. Pure functions; all thresholds are arguments."""

from __future__ import annotations


def classify(
    ax1_val: float,
    ax2_val: float,
    ax2_mean_val: float,
    direction_val: float,
    *,
    ax1_weak: float,
    ax1_strong: float,
    vol_lo: float,
    vol_hi: float,
    direction_band: float,
    direction_center: float = 50.0,
) -> tuple[int, int, str | None]:
    """Classify one decision point into ``(ax1_class, ax2_class, direction)``.

    - ``ax1_class``: trend strength, 0 (weak) / 1 (mid) / 2 (strong)
    - ``ax2_class``: volatility vs its rolling mean, 0 (low) / 1 (normal) / 2 (high)
    - ``direction``: "BUY" / "SELL", or ``None`` inside the neutral band
    """
    ax1_class = 0 if ax1_val < ax1_weak else (1 if ax1_val < ax1_strong else 2)

    ratio = ax2_val / ax2_mean_val if ax2_mean_val > 0 else 1.0
    ax2_class = 0 if ratio < vol_lo else (1 if ratio < vol_hi else 2)

    neutral_lo = direction_center - direction_band
    neutral_hi = direction_center + direction_band
    direction = (
        None
        if neutral_lo <= direction_val <= neutral_hi
        else ("SELL" if direction_val < neutral_lo else "BUY")
    )
    return ax1_class, ax2_class, direction
