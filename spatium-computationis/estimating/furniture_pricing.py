"""
Estimating — Furniture Pricing Logic  ◈$

Reference tables and heuristics used by Estimator Mobilia when
vendor pricing is not available.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Complexity multipliers for commercial FF&E
# ---------------------------------------------------------------------------

COMPLEXITY_MULTIPLIERS = {
    "low": 1.0,       # standard catalogue items, simple assembly
    "medium": 1.25,   # custom finishes, moderate assembly
    "high": 1.5,      # fully custom, complex coordination
    "extreme": 2.0,   # bespoke/architectural integration
}

# Freight as % of product cost (typical commercial range)
FREIGHT_PCT_LOW = 0.08
FREIGHT_PCT_HIGH = 0.12
FREIGHT_PCT_DEFAULT = 0.10

# ---------------------------------------------------------------------------
# Rough category pricing ($/unit, commercial grade)
# ---------------------------------------------------------------------------

CATEGORY_PRICING: dict[str, tuple[float, float]] = {
    # category: (low_estimate, high_estimate)
    "task_chair": (400, 1200),
    "lounge_chair": (600, 3000),
    "sofa": (1500, 8000),
    "conference_table": (2000, 15000),
    "desk": (800, 4000),
    "credenza": (1200, 6000),
    "bookcase": (400, 2000),
    "filing_cabinet": (300, 800),
    "side_table": (200, 1200),
    "dining_table": (800, 5000),
    "dining_chair": (200, 800),
    "bar_stool": (200, 600),
    "bed": (600, 4000),
    "dresser": (800, 3000),
    "nightstand": (200, 1000),
    "wardrobe": (1000, 5000),
    "reception_desk": (3000, 20000),
    "panel_system": (500, 2000),   # per panel/station
    "storage_wall": (2000, 12000),
}


def estimate_unit_price(category: str, complexity: str = "medium") -> float | None:
    """Return a mid-point price estimate for a furniture category."""
    if category not in CATEGORY_PRICING:
        return None
    low, high = CATEGORY_PRICING[category]
    mid = (low + high) / 2
    return round(mid * COMPLEXITY_MULTIPLIERS.get(complexity, 1.25), 2)


def freight_estimate(product_subtotal: float, pct: float = FREIGHT_PCT_DEFAULT) -> float:
    return round(product_subtotal * pct, 2)
