"""
📊 ADAPTIVE STATE REGISTRY — Real-Time Observable Cognitive Ledger

Exposes the living state of ANIMUS to monitoring, dashboards, and external systems.
This is the transparency layer that proves the system is truly adaptive:
- Mind embeddings visibly drift over time
- Activation levels change based on context
- Learning velocity is measurable
- Effectiveness metric oscillates (not stuck at 1.0)

Glyph: 📊🧠⚡ (observable adaptive intelligence)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MindActivationSnapshot(BaseModel):
    """Current activation state of a single mind."""
    mind_name: str
    activation_level: float = Field(ge=0.0, le=1.0)
    embedding_norm: float = Field(ge=0.0, description="Magnitude of embedding vector")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class AdaptiveStateRecord(BaseModel):
    """A timestamped snapshot of the entire adaptive system state."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Cognitive metrics
    system_effectiveness: float = Field(ge=0.0, le=1.0)
    should_explore: bool
    entropy_level: float = Field(ge=0.0, le=1.0)
    prediction_error: float = Field(ge=0.0, le=1.0)
    
    # Mind states
    mind_activations: list[MindActivationSnapshot] = Field(default_factory=list)
    
    # Learning metrics
    learning_velocity: float = Field(
        description="Rate of change in mind embeddings (0-1)"
    )
    total_learning_signals: int = Field(description="Cumulative signals processed")
    recent_signal_rate: float = Field(
        description="Signals per minute (last window)"
    )
    
    # System health
    total_perceptions: int
    explore_activations: int
    
    # Metadata
    version: str = "v1_adaptive"


class AdaptiveStateRegistry:
    """
    📊 Central registry of the adaptive system's observable state.
    
    This enables:
    1. Real-time monitoring dashboards (Vigil Operis can subscribe)
    2. Proof that minds are actually learning and changing
    3. Detection of maladaptive states (e.g., entropy stuck at 0)
    4. Analysis of learning curves over time
    """
    
    def __init__(self, max_history: int = 1000):
        self.records: list[AdaptiveStateRecord] = []
        self.max_history = max_history
        self.last_signal_timestamp = datetime.now(timezone.utc)
        self.signal_count_window = 0
    
    def record_state(
        self,
        system_effectiveness: float,
        should_explore: bool,
        entropy_level: float,
        prediction_error: float,
        mind_activations: list[MindActivationSnapshot],
        learning_velocity: float,
        total_learning_signals: int,
        total_perceptions: int,
        explore_activations: int,
    ) -> AdaptiveStateRecord:
        """
        Record a snapshot of the adaptive system's state.
        
        Called periodically (e.g., every perception, or every N perceptions)
        to build a timeline of system evolution.
        """
        now = datetime.now(timezone.utc)
        
        # Calculate signal rate
        time_delta = (now - self.last_signal_timestamp).total_seconds()
        if time_delta > 60:  # Window is 60 seconds
            recent_signal_rate = self.signal_count_window / (time_delta / 60.0)
            self.signal_count_window = 0
            self.last_signal_timestamp = now
        else:
            self.signal_count_window += 1
            recent_signal_rate = 0.0  # Not yet a full window
        
        record = AdaptiveStateRecord(
            timestamp=now,
            system_effectiveness=system_effectiveness,
            should_explore=should_explore,
            entropy_level=entropy_level,
            prediction_error=prediction_error,
            mind_activations=mind_activations,
            learning_velocity=learning_velocity,
            total_learning_signals=total_learning_signals,
            recent_signal_rate=recent_signal_rate,
            total_perceptions=total_perceptions,
            explore_activations=explore_activations,
        )
        
        self.records.append(record)
        if len(self.records) > self.max_history:
            self.records = self.records[-self.max_history:]
        
        return record
    
    def get_current_state(self) -> dict[str, Any] | None:
        """Get the most recent state snapshot."""
        if not self.records:
            return None
        
        latest = self.records[-1]
        return {
            "timestamp": latest.timestamp.isoformat(),
            "system_effectiveness": round(latest.system_effectiveness, 4),
            "should_explore": latest.should_explore,
            "entropy_level": round(latest.entropy_level, 4),
            "prediction_error": round(latest.prediction_error, 4),
            "minds": [
                {
                    "name": m.mind_name,
                    "activation": round(m.activation_level, 4),
                    "embedding_norm": round(m.embedding_norm, 4),
                    "confidence": round(m.confidence, 4),
                }
                for m in latest.mind_activations
            ],
            "learning_velocity": round(latest.learning_velocity, 4),
            "total_learning_signals": latest.total_learning_signals,
            "total_perceptions": latest.total_perceptions,
            "explore_activations": latest.explore_activations,
        }
    
    def get_state_timeline(
        self,
        limit: int = 100,
        metric: str | None = None,
    ) -> dict[str, Any]:
        """
        Get a timeline of state changes.
        
        Args:
            limit: How many records to return
            metric: If specified, only include this metric (e.g., 'system_effectiveness')
        
        Returns:
            Timeline as dict with timestamps and values
        """
        records = self.records[-limit:]
        
        if not records:
            return {
                "metric": metric or "all",
                "records": [],
                "count": 0,
            }
        
        if metric == "system_effectiveness":
            timeline = [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "value": round(r.system_effectiveness, 4),
                }
                for r in records
            ]
        
        elif metric == "entropy_level":
            timeline = [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "value": round(r.entropy_level, 4),
                    "should_explore": r.should_explore,
                }
                for r in records
            ]
        
        elif metric == "prediction_error":
            timeline = [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "value": round(r.prediction_error, 4),
                }
                for r in records
            ]
        
        else:
            # Full timeline
            timeline = [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "effectiveness": round(r.system_effectiveness, 4),
                    "entropy": round(r.entropy_level, 4),
                    "error": round(r.prediction_error, 4),
                    "velocity": round(r.learning_velocity, 4),
                }
                for r in records
            ]
        
        return {
            "metric": metric or "all",
            "records": timeline,
            "count": len(timeline),
        }
    
    def get_learning_curve(self) -> dict[str, Any]:
        """
        Get the learning curve: how fast embeddings are changing.
        
        Returns metrics that prove the system is actually learning.
        """
        if len(self.records) < 2:
            return {"count": 0, "learning_velocity_avg": 0.0}
        
        velocities = [r.learning_velocity for r in self.records[-50:]]
        signals = [r.total_learning_signals for r in self.records[-50:]]
        
        return {
            "count": len(velocities),
            "learning_velocity_avg": round(sum(velocities) / len(velocities), 4) if velocities else 0.0,
            "learning_velocity_max": round(max(velocities), 4) if velocities else 0.0,
            "learning_velocity_min": round(min(velocities), 4) if velocities else 0.0,
            "signals_processed": signals[-1] if signals else 0,
            "signals_delta_last_50": signals[-1] - signals[0] if len(signals) > 1 else 0,
        }
    
    def get_homeostat_health(self) -> dict[str, Any]:
        """
        Check if the homeostat is functioning correctly.
        
        Indicates whether:
        - Effectiveness oscillates (not stuck)
        - Explore branch fires occasionally
        - Entropy changes (not frozen at 0)
        """
        if len(self.records) < 10:
            return {
                "status": "insufficient_data",
                "min_records_needed": 10,
                "records_available": len(self.records),
            }
        
        recent = self.records[-50:]
        
        # Check effectiveness oscillation
        effectiveness_values = [r.system_effectiveness for r in recent]
        effectiveness_range = max(effectiveness_values) - min(effectiveness_values)
        
        # Check explore activations
        explore_count = sum(1 for r in recent if r.should_explore)
        
        # Check entropy change
        entropy_values = [r.entropy_level for r in recent]
        entropy_range = max(entropy_values) - min(entropy_values)
        
        # Determine health
        is_healthy = (
            effectiveness_range > 0.1 and  # Effectiveness varies
            explore_count > 2 and  # Explore fires occasionally
            entropy_range > 0.05  # Entropy is not frozen
        )
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "effectiveness_range": round(effectiveness_range, 4),
            "effectiveness_varies": effectiveness_range > 0.1,
            "explore_activations_recent": explore_count,
            "entropy_range": round(entropy_range, 4),
            "entropy_varies": entropy_range > 0.05,
            "diagnostics": {
                "min_effectiveness": round(min(effectiveness_values), 4),
                "max_effectiveness": round(max(effectiveness_values), 4),
                "min_entropy": round(min(entropy_values), 4),
                "max_entropy": round(max(entropy_values), 4),
            }
        }
    
    def export_for_dashboard(self) -> dict[str, Any]:
        """
        Export state for Vigil Operis dashboard.
        
        This is what the dashboard shows to prove the system is alive and learning.
        """
        return {
            "type": "adaptive_state_snapshot",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_state": self.get_current_state(),
            "learning_curve": self.get_learning_curve(),
            "homeostat_health": self.get_homeostat_health(),
            "recent_timeline": self.get_state_timeline(limit=20),
            "schema_version": "v1",
        }


# ---------------------------------------------------------------------------
# Singleton Registry
# ---------------------------------------------------------------------------

_registry_instance: AdaptiveStateRegistry | None = None


def get_adaptive_state_registry() -> AdaptiveStateRegistry:
    """Get or create the singleton adaptive state registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AdaptiveStateRegistry()
    return _registry_instance
