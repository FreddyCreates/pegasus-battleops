"""
ARCHON Cortex — Persistent Cognitive State

The Cortex is the working memory and situational awareness layer of ARCHON.
It maintains:
  - Working Memory: recent signals, decisions, and context (72hr window)
  - Situational Awareness: current threat map, resource state, posture history
  - Temporal Patterns: signal frequency, drift detection, baseline comparisons
  - Specimen Correlation: links ARCHON observations to organism specimen profiles

The Cortex is what makes ARCHON a brain rather than a calculator.
It remembers. It correlates. It detects drift.

Glyph: 🧬 (cognitive DNA — persistent substrate)
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .minds import MindType, PostureMode, ThreatVector


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "archon.db"


def _init_cortex_db() -> None:
    """Initialize cortex tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Working memory — recent observations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cortex_memory (
                memory_id       TEXT PRIMARY KEY,
                memory_type     TEXT NOT NULL,
                mind_source     TEXT,
                content         TEXT NOT NULL,
                signal_value    REAL,
                confidence      REAL,
                threat_vectors  TEXT DEFAULT '[]',
                context_hash    TEXT,
                decay_factor    REAL DEFAULT 1.0,
                created_at      TEXT NOT NULL,
                expires_at      TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cm_type ON cortex_memory(memory_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cm_created ON cortex_memory(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cm_expires ON cortex_memory(expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cm_hash ON cortex_memory(context_hash)")

        # Threat map — active and historical threats
        conn.execute("""
            CREATE TABLE IF NOT EXISTS threat_map (
                threat_id       TEXT PRIMARY KEY,
                vector          TEXT NOT NULL,
                source_ip       TEXT,
                specimen_id     TEXT,
                severity        REAL NOT NULL,
                confidence      REAL NOT NULL,
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                correlated_with TEXT DEFAULT '[]',
                status          TEXT DEFAULT 'active',
                mind_attribution TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tm_vector ON threat_map(vector)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tm_status ON threat_map(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tm_severity ON threat_map(severity)")

        # Baseline metrics — what 'normal' looks like
        conn.execute("""
            CREATE TABLE IF NOT EXISTS baselines (
                metric_name     TEXT PRIMARY KEY,
                mean_value      REAL NOT NULL,
                std_deviation   REAL NOT NULL,
                sample_count    INTEGER DEFAULT 0,
                last_updated    TEXT NOT NULL,
                drift_detected  INTEGER DEFAULT 0
            )
        """)

        # Posture history
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posture_history (
                transition_id   TEXT PRIMARY KEY,
                from_posture    TEXT NOT NULL,
                to_posture      TEXT NOT NULL,
                trigger_reason  TEXT,
                triggered_by    TEXT,
                alert_level     REAL,
                created_at      TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ph_created ON posture_history(created_at)")

        # Signal frequency tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signal_frequency (
                mind_type       TEXT NOT NULL,
                hour_bucket     TEXT NOT NULL,
                signal_count    INTEGER DEFAULT 0,
                avg_value       REAL DEFAULT 0.0,
                avg_confidence  REAL DEFAULT 0.0,
                threat_count    INTEGER DEFAULT 0,
                PRIMARY KEY (mind_type, hour_bucket)
            )
        """)

        conn.commit()


_init_cortex_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cortex Models
# ---------------------------------------------------------------------------

class ThreatMapEntry(BaseModel):
    """An active threat in the cortex threat map."""
    threat_id: str
    vector: ThreatVector
    source_ip: str | None = None
    specimen_id: str | None = None
    severity: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int = 1
    correlated_with: list[str] = Field(default_factory=list)
    status: str = "active"
    mind_attribution: MindType | None = None


class WorkingMemory(BaseModel):
    """A single entry in the cortex working memory."""
    memory_id: str
    memory_type: str  # "signal", "decision", "observation", "correlation"
    mind_source: MindType | None = None
    content: str
    signal_value: float | None = None
    confidence: float | None = None
    threat_vectors: list[ThreatVector] = Field(default_factory=list)
    context_hash: str | None = None
    decay_factor: float = 1.0
    created_at: datetime
    expires_at: datetime


class BaselineMetric(BaseModel):
    """Statistical baseline for drift detection."""
    metric_name: str
    mean_value: float
    std_deviation: float
    sample_count: int = 0
    last_updated: datetime
    drift_detected: bool = False


class SituationalAwareness(BaseModel):
    """Current cognitive state snapshot — what ARCHON 'sees' right now."""
    current_posture: PostureMode = PostureMode.PATROL
    alert_level: float = 0.0
    active_threats: list[ThreatMapEntry] = Field(default_factory=list)
    recent_memories: list[WorkingMemory] = Field(default_factory=list)
    baseline_drift: dict[str, float] = Field(default_factory=dict)
    signal_frequency: dict[MindType, float] = Field(default_factory=dict)
    last_decision_at: datetime | None = None
    uptime_hours: float = 0.0
    total_decisions: int = 0
    posture_stability_hours: float = 0.0


class CortexState(BaseModel):
    """Full cortex dump — complete cognitive state for serialization."""
    awareness: SituationalAwareness
    threat_map_size: int = 0
    memory_size: int = 0
    oldest_memory: datetime | None = None
    newest_memory: datetime | None = None
    baseline_count: int = 0


# ---------------------------------------------------------------------------
# Cortex Operations
# ---------------------------------------------------------------------------

def store_memory(
    memory_type: str,
    content: str,
    mind_source: MindType | None = None,
    signal_value: float | None = None,
    confidence: float | None = None,
    threat_vectors: list[ThreatVector] | None = None,
    ttl_hours: int = 72,
) -> str:
    """Store a new observation in working memory.

    Default TTL is 72 hours per AI Intelligence doctrine.
    """
    memory_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=ttl_hours)
    context_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    with _db() as conn:
        conn.execute("""
            INSERT INTO cortex_memory
            (memory_id, memory_type, mind_source, content, signal_value,
             confidence, threat_vectors, context_hash, decay_factor, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, memory_type,
            mind_source.value if mind_source else None,
            content, signal_value, confidence,
            json.dumps([tv.value for tv in (threat_vectors or [])]),
            context_hash, 1.0, now.isoformat(), expires.isoformat(),
        ))
        conn.commit()

    return memory_id


def recall_memories(
    memory_type: str | None = None,
    mind_source: MindType | None = None,
    limit: int = 50,
    include_expired: bool = False,
) -> list[WorkingMemory]:
    """Recall memories from the cortex, applying temporal decay."""
    now = datetime.now(timezone.utc)

    with _db() as conn:
        query = "SELECT * FROM cortex_memory WHERE 1=1"
        params: list[Any] = []

        if not include_expired:
            query += " AND expires_at > ?"
            params.append(now.isoformat())
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        if mind_source:
            query += " AND mind_source = ?"
            params.append(mind_source.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

        memories = []
        for row in rows:
            created = datetime.fromisoformat(row["created_at"])
            # Temporal decay: signal strength reduces over time
            age_hours = (now - created).total_seconds() / 3600
            # Exponential decay: λ=0.02/hr gives half-life ≈ 34.7hr (ln2/0.02)
            # This means a signal loses ~50% strength after ~35 hours,
            # aligning with the 72hr working memory window (signal < 24% at expiry)
            decay = math.exp(-0.02 * age_hours)

            memories.append(WorkingMemory(
                memory_id=row["memory_id"],
                memory_type=row["memory_type"],
                mind_source=MindType(row["mind_source"]) if row["mind_source"] else None,
                content=row["content"],
                signal_value=(row["signal_value"] * decay) if row["signal_value"] else None,
                confidence=row["confidence"],
                threat_vectors=[ThreatVector(tv) for tv in json.loads(row["threat_vectors"])],
                context_hash=row["context_hash"],
                decay_factor=decay,
                created_at=created,
                expires_at=datetime.fromisoformat(row["expires_at"]),
            ))

        return memories


def register_threat(
    vector: ThreatVector,
    severity: float,
    confidence: float,
    source_ip: str | None = None,
    specimen_id: str | None = None,
    mind_attribution: MindType | None = None,
    correlated_with: list[str] | None = None,
) -> ThreatMapEntry:
    """Register a new threat or update existing one in the threat map."""
    now = datetime.now(timezone.utc)

    with _db() as conn:
        # Check for existing similar threat
        existing = None
        if source_ip:
            existing = conn.execute(
                "SELECT * FROM threat_map WHERE vector = ? AND source_ip = ? AND status = 'active'",
                (vector.value, source_ip),
            ).fetchone()

        if existing:
            # Update existing
            new_count = existing["occurrence_count"] + 1
            # Severity increases with repeated observations
            new_severity = min(1.0, existing["severity"] + 0.05)
            # Confidence increases with corroboration
            new_confidence = min(1.0, existing["confidence"] + 0.03)

            correlations = json.loads(existing["correlated_with"])
            if correlated_with:
                correlations.extend(correlated_with)
                correlations = list(set(correlations))[-20:]  # Keep last 20

            conn.execute("""
                UPDATE threat_map SET
                    severity = ?, confidence = ?, last_seen = ?,
                    occurrence_count = ?, correlated_with = ?
                WHERE threat_id = ?
            """, (
                new_severity, new_confidence, now.isoformat(),
                new_count, json.dumps(correlations), existing["threat_id"],
            ))
            conn.commit()

            return ThreatMapEntry(
                threat_id=existing["threat_id"],
                vector=vector,
                source_ip=source_ip,
                specimen_id=specimen_id,
                severity=new_severity,
                confidence=new_confidence,
                first_seen=datetime.fromisoformat(existing["first_seen"]),
                last_seen=now,
                occurrence_count=new_count,
                correlated_with=correlations,
                status="active",
                mind_attribution=mind_attribution,
            )

        # Create new threat
        threat_id = str(uuid.uuid4())
        entry = ThreatMapEntry(
            threat_id=threat_id,
            vector=vector,
            source_ip=source_ip,
            specimen_id=specimen_id,
            severity=severity,
            confidence=confidence,
            first_seen=now,
            last_seen=now,
            occurrence_count=1,
            correlated_with=correlated_with or [],
            status="active",
            mind_attribution=mind_attribution,
        )

        conn.execute("""
            INSERT INTO threat_map
            (threat_id, vector, source_ip, specimen_id, severity, confidence,
             first_seen, last_seen, occurrence_count, correlated_with, status, mind_attribution)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            threat_id, vector.value, source_ip, specimen_id,
            severity, confidence, now.isoformat(), now.isoformat(),
            1, json.dumps(correlated_with or []), "active",
            mind_attribution.value if mind_attribution else None,
        ))
        conn.commit()

    return entry


def get_active_threats(min_severity: float = 0.0) -> list[ThreatMapEntry]:
    """Get all active threats from the threat map."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM threat_map WHERE status = 'active' AND severity >= ? ORDER BY severity DESC",
            (min_severity,),
        ).fetchall()

        return [
            ThreatMapEntry(
                threat_id=row["threat_id"],
                vector=ThreatVector(row["vector"]),
                source_ip=row["source_ip"],
                specimen_id=row["specimen_id"],
                severity=row["severity"],
                confidence=row["confidence"],
                first_seen=datetime.fromisoformat(row["first_seen"]),
                last_seen=datetime.fromisoformat(row["last_seen"]),
                occurrence_count=row["occurrence_count"],
                correlated_with=json.loads(row["correlated_with"]),
                status=row["status"],
                mind_attribution=MindType(row["mind_attribution"]) if row["mind_attribution"] else None,
            )
            for row in rows
        ]


def update_baseline(metric_name: str, new_value: float) -> tuple[float, bool]:
    """Update a baseline metric with a new observation.

    Returns (drift_sigma, drift_detected) — how many standard deviations
    the new value is from the mean, and whether drift threshold was exceeded.
    """
    now = datetime.now(timezone.utc)

    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM baselines WHERE metric_name = ?", (metric_name,)
        ).fetchone()

        if row:
            # Online mean/std update (Welford's algorithm)
            n = row["sample_count"] + 1
            old_mean = row["mean_value"]
            old_std = row["std_deviation"]

            delta = new_value - old_mean
            new_mean = old_mean + delta / n

            # Update variance
            if n > 1:
                old_variance = old_std ** 2
                new_variance = old_variance + (delta * (new_value - new_mean) - old_variance) / n
                new_std = math.sqrt(max(0.0, new_variance))
            else:
                new_std = 0.0

            # Drift detection: > 2σ from mean
            drift_sigma = abs(delta) / old_std if old_std > 0 else 0.0
            drift_detected = drift_sigma > 2.0

            conn.execute("""
                UPDATE baselines SET mean_value = ?, std_deviation = ?,
                sample_count = ?, last_updated = ?, drift_detected = ?
                WHERE metric_name = ?
            """, (new_mean, new_std, n, now.isoformat(), 1 if drift_detected else 0, metric_name))
            conn.commit()

            return drift_sigma, drift_detected
        else:
            # First observation — initialize baseline
            conn.execute("""
                INSERT INTO baselines (metric_name, mean_value, std_deviation, sample_count, last_updated, drift_detected)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (metric_name, new_value, 0.0, 1, now.isoformat(), 0))
            conn.commit()

            return 0.0, False


def record_posture_transition(
    from_posture: PostureMode,
    to_posture: PostureMode,
    trigger_reason: str,
    triggered_by: MindType | None = None,
    alert_level: float = 0.0,
) -> None:
    """Record a posture transition in the cortex."""
    now = datetime.now(timezone.utc)
    with _db() as conn:
        conn.execute("""
            INSERT INTO posture_history
            (transition_id, from_posture, to_posture, trigger_reason, triggered_by, alert_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), from_posture.value, to_posture.value,
            trigger_reason, triggered_by.value if triggered_by else None,
            alert_level, now.isoformat(),
        ))
        conn.commit()


def record_signal_frequency(mind_type: MindType, signal_value: float, confidence: float, has_threat: bool) -> None:
    """Record signal frequency for pattern analysis."""
    now = datetime.now(timezone.utc)
    hour_bucket = now.strftime("%Y-%m-%dT%H")

    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM signal_frequency WHERE mind_type = ? AND hour_bucket = ?",
            (mind_type.value, hour_bucket),
        ).fetchone()

        if row:
            n = row["signal_count"] + 1
            new_avg_val = row["avg_value"] + (signal_value - row["avg_value"]) / n
            new_avg_conf = row["avg_confidence"] + (confidence - row["avg_confidence"]) / n
            threat_count = row["threat_count"] + (1 if has_threat else 0)

            conn.execute("""
                UPDATE signal_frequency SET signal_count = ?, avg_value = ?,
                avg_confidence = ?, threat_count = ?
                WHERE mind_type = ? AND hour_bucket = ?
            """, (n, new_avg_val, new_avg_conf, threat_count, mind_type.value, hour_bucket))
        else:
            conn.execute("""
                INSERT INTO signal_frequency (mind_type, hour_bucket, signal_count, avg_value, avg_confidence, threat_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (mind_type.value, hour_bucket, 1, signal_value, confidence, 1 if has_threat else 0))

        conn.commit()


def get_situational_awareness() -> SituationalAwareness:
    """Build the current situational awareness snapshot."""
    now = datetime.now(timezone.utc)

    active_threats = get_active_threats()
    recent_memories = recall_memories(limit=20)

    # Get signal frequency for last hour
    hour_bucket = now.strftime("%Y-%m-%dT%H")
    signal_freq: dict[MindType, float] = {}
    with _db() as conn:
        rows = conn.execute(
            "SELECT mind_type, signal_count FROM signal_frequency WHERE hour_bucket = ?",
            (hour_bucket,),
        ).fetchall()
        for row in rows:
            signal_freq[MindType(row["mind_type"])] = float(row["signal_count"])

        # Get last posture
        last_posture_row = conn.execute(
            "SELECT to_posture, created_at FROM posture_history ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

        current_posture = PostureMode.PATROL
        posture_stability = 0.0
        if last_posture_row:
            current_posture = PostureMode(last_posture_row["to_posture"])
            last_change = datetime.fromisoformat(last_posture_row["created_at"])
            posture_stability = (now - last_change).total_seconds() / 3600

        # Baseline drift
        drift_rows = conn.execute(
            "SELECT metric_name, drift_detected FROM baselines WHERE drift_detected = 1"
        ).fetchall()
        baseline_drift = {row["metric_name"]: 1.0 for row in drift_rows}

    # Compute alert level from threat map
    if active_threats:
        max_severity = max(t.severity for t in active_threats)
        avg_severity = sum(t.severity for t in active_threats) / len(active_threats)
        alert_level = min(1.0, (max_severity * 0.7 + avg_severity * 0.3))
    else:
        alert_level = 0.0

    return SituationalAwareness(
        current_posture=current_posture,
        alert_level=alert_level,
        active_threats=active_threats,
        recent_memories=recent_memories,
        baseline_drift=baseline_drift,
        signal_frequency=signal_freq,
        posture_stability_hours=posture_stability,
    )


def prune_expired() -> int:
    """Prune expired memories and resolved threats. Returns count pruned."""
    now = datetime.now(timezone.utc)
    pruned = 0

    with _db() as conn:
        # Expire old memories
        result = conn.execute(
            "DELETE FROM cortex_memory WHERE expires_at < ?",
            (now.isoformat(),),
        )
        pruned += result.rowcount

        # Archive old threats (> 7 days since last seen)
        cutoff = (now - timedelta(days=7)).isoformat()
        result = conn.execute(
            "UPDATE threat_map SET status = 'archived' WHERE status = 'active' AND last_seen < ?",
            (cutoff,),
        )
        pruned += result.rowcount

        conn.commit()

    return pruned
