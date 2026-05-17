"""
Estimating — Labor Pricing Logic  ⚒$

Reference tables and heuristics used by Estimator Laboris when
pricing installation scope.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Labor rates ($/hr, commercial installation)
# ---------------------------------------------------------------------------

CREW_RATES = {
    "installer": 75.0,
    "lead_installer": 90.0,
    "foreman": 110.0,
    "driver": 65.0,
}

# Minimum call-out per person (hours)
MINIMUM_CALL = 4.0

# Overtime threshold (hours per day before OT kicks in)
OT_THRESHOLD = 8.0
OT_MULTIPLIER = 1.5

# ---------------------------------------------------------------------------
# Per-item time estimates (hours/unit) for common furniture categories
# ---------------------------------------------------------------------------

ASSEMBLY_HOURS_PER_UNIT: dict[str, float] = {
    "task_chair": 0.25,
    "lounge_chair": 0.5,
    "sofa": 1.0,
    "conference_table": 2.0,
    "desk": 1.0,
    "credenza": 1.5,
    "bookcase": 0.75,
    "filing_cabinet": 0.25,
    "side_table": 0.25,
    "panel_system": 2.0,   # per station
    "reception_desk": 4.0,
    "storage_wall": 3.0,
}

PLACEMENT_HOURS_PER_UNIT: dict[str, float] = {
    "task_chair": 0.1,
    "lounge_chair": 0.2,
    "sofa": 0.5,
    "conference_table": 1.0,
    "desk": 0.5,
    "credenza": 0.5,
    "bookcase": 0.3,
    "filing_cabinet": 0.15,
    "panel_system": 0.5,
    "reception_desk": 1.0,
}

# Complexity adjustments
COMPLEXITY_ADJUSTMENTS = {
    "low": 0.8,
    "medium": 1.0,
    "high": 1.3,
    "extreme": 1.75,
}


def estimate_assembly_hours(
    category: str, quantity: int, complexity: str = "medium"
) -> float:
    base = ASSEMBLY_HOURS_PER_UNIT.get(category, 0.5)
    return round(base * quantity * COMPLEXITY_ADJUSTMENTS.get(complexity, 1.0), 2)


def crew_cost(crew_size: int, hours: float, role: str = "installer") -> float:
    effective_hours = max(hours, MINIMUM_CALL)
    rate = CREW_RATES.get(role, CREW_RATES["installer"])
    return round(crew_size * effective_hours * rate, 2)
