"""
Protocols Package — Spatium Computationis

The five-plus-one protocol pipeline:
  I.   Ingressus  — raw input normalization
  II.  Compressio — compression into intelligence objects
  III. Ordinatio  — routing decisions
  IV.  Actio      — action execution
  V.   Reductus   — field feedback loop
  VI.  Feedback   — learning and weight adjustment

Glyphs:
  ⊕ Ingressus  — input gate
  ⌬ Compressio — compression
  ≡ Ordinatio  — routing
  ⚡ Actio      — execution
  ↺ Reductus   — field return
  ⟲ Feedback   — learning loop
"""
from . import ingressus, compressio, ordinatio, actio, reductus, feedback

__all__ = ["ingressus", "compressio", "ordinatio", "actio", "reductus", "feedback"]
