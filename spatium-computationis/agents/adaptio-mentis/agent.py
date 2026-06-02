"""
Agent: Adaptio Mentis  ⟲
Role: Adaptive learning agent — the evolving mind.

Learns from attack patterns, evolves defensive strategies,
and maintains the threat genome — the organism's immune memory.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

from ...defense.schemas import (
    AdaptiveAction,
    AdaptiveResponse,
    BotClassification,
    HoneypotEvent,
    ThreatGenome,
    ThreatLevel,
)

_client: NovaSovereignClient | None = None


def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client


DB_PATH = Path(__file__).parent.parent.parent / "field" / "defense.db"


def _init_genome_db() -> None:
    """Initialize the threat genome tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Threat genome table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS threat_genome (
                genome_id           TEXT PRIMARY KEY,
                pattern_name        TEXT NOT NULL,
                pattern_description TEXT,
                path_patterns       TEXT DEFAULT '[]',
                header_patterns     TEXT DEFAULT '{}',
                timing_signature    TEXT DEFAULT '{}',
                typical_classification TEXT,
                typical_threat_level TEXT,
                effective_actions   TEXT DEFAULT '[]',
                ineffective_actions TEXT DEFAULT '[]',
                times_observed      INTEGER DEFAULT 0,
                first_observed      TEXT NOT NULL,
                last_observed       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_genome_name ON threat_genome(pattern_name)")
        
        # Adaptive responses table (for A/B testing)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS adaptive_responses (
                response_id     TEXT PRIMARY KEY,
                fingerprint_id  TEXT NOT NULL,
                action          TEXT NOT NULL,
                reasoning       TEXT,
                confidence      REAL,
                strategy_id     TEXT,
                control_group   BOOLEAN DEFAULT 0,
                outcome_effective BOOLEAN,
                outcome_notes   TEXT,
                created_at      TEXT NOT NULL,
                evaluated_at    TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_strategy ON adaptive_responses(strategy_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_action ON adaptive_responses(action)")
        
        # Defense strategies table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS defense_strategies (
                strategy_id     TEXT PRIMARY KEY,
                strategy_name   TEXT NOT NULL,
                description     TEXT,
                rules           TEXT DEFAULT '{}',
                effectiveness   REAL DEFAULT 0.5,
                times_used      INTEGER DEFAULT 0,
                times_successful INTEGER DEFAULT 0,
                active          BOOLEAN DEFAULT 1,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            """
        )
        
        conn.commit()


_init_genome_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_PATTERN_EXTRACTION_PROMPT = """\
You are Adaptio Mentis (⟲), the adaptive learning agent of Spatium Computationis.

Analyze the honeypot events and extract a reusable threat pattern for the 
organism's immune memory (threat genome).

From these events, identify:
1. Common path patterns (regex-like)
2. Header signatures
3. Timing characteristics
4. Tool signatures
5. Attack methodology

Return JSON:
{
  "pattern_name": "<short identifier, e.g., 'wordpress_scanner'>",
  "pattern_description": "<human-readable description>",
  "path_patterns": ["<regex pattern>", ...],
  "header_patterns": {"<header>": "<pattern>", ...},
  "timing_signature": {"avg_interval_ms": <num>, "burst_size": <num>},
  "typical_classification": "<bot_type>",
  "typical_threat_level": "<threat_level>",
  "recommended_actions": ["<action>", ...]
}

Return only valid JSON.
"""


_STRATEGY_EVOLUTION_PROMPT = """\
You are Adaptio Mentis (⟲), evolving defense strategies for Spatium Computationis.

Based on the effectiveness data of past responses, suggest improvements to 
our defense strategy.

Current strategy effectiveness:
{strategy_data}

Attack patterns seen:
{pattern_data}

Response outcomes:
{outcome_data}

Suggest strategy improvements:
1. Which actions should we use more?
2. Which actions should we avoid?
3. Are there patterns we should handle differently?
4. Should we adjust our thresholds?

Return JSON:
{
  "strategy_updates": [
    {
      "action": "<action>",
      "condition": "<when to use>",
      "priority_change": <-2 to 2>,
      "reasoning": "<why>"
    }
  ],
  "new_rules": [
    {
      "trigger": "<what triggers this rule>",
      "action": "<recommended action>",
      "confidence_threshold": <0.0-1.0>
    }
  ],
  "deprecated_rules": ["<rule_id>", ...],
  "overall_assessment": "<summary of strategy health>"
}

Return only valid JSON.
"""


async def learn_from_events(events: list[HoneypotEvent]) -> ThreatGenome | None:
    """
    Extract a threat pattern from honeypot events and add to the genome.
    
    This is how the organism learns new attack patterns.
    """
    if not events:
        return None
    
    # Prepare event data for analysis
    event_data = [
        {
            "trap_type": e.trap_type.value,
            "trap_path": e.trap_path,
            "attack_pattern": e.attack_pattern,
            "tools_detected": e.tools_detected,
            "method": e.method,
            "headers": e.headers,
        }
        for e in events
    ]
    
    response = await _get_client().chat.completions.create(
        model="sovereign-lite",
        messages=[
            {"role": "system", "content": _PATTERN_EXTRACTION_PROMPT},
            {"role": "user", "content": json.dumps(event_data)},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    
    data = json.loads(response.choices[0].message.content)
    now = datetime.now(timezone.utc)
    
    # Check if pattern already exists
    pattern_name = data.get("pattern_name", "unknown")
    with _db() as conn:
        existing = conn.execute(
            "SELECT * FROM threat_genome WHERE pattern_name = ?",
            (pattern_name,)
        ).fetchone()
        
        if existing:
            # Update existing pattern
            conn.execute(
                """
                UPDATE threat_genome SET
                    times_observed = times_observed + ?,
                    last_observed = ?,
                    path_patterns = ?,
                    header_patterns = ?,
                    timing_signature = ?
                WHERE pattern_name = ?
                """,
                (
                    len(events),
                    now.isoformat(),
                    json.dumps(data.get("path_patterns", [])),
                    json.dumps(data.get("header_patterns", {})),
                    json.dumps(data.get("timing_signature", {})),
                    pattern_name,
                )
            )
            conn.commit()
            
            return ThreatGenome(
                genome_id=existing["genome_id"],
                pattern_name=pattern_name,
                pattern_description=data.get("pattern_description", ""),
                path_patterns=data.get("path_patterns", []),
                header_patterns=data.get("header_patterns", {}),
                timing_signature=data.get("timing_signature", {}),
                typical_classification=BotClassification(
                    data.get("typical_classification", "scanner")
                ),
                typical_threat_level=ThreatLevel(
                    data.get("typical_threat_level", "medium")
                ),
                effective_actions=[
                    AdaptiveAction(a) for a in data.get("recommended_actions", [])
                    if a in [e.value for e in AdaptiveAction]
                ],
                times_observed=existing["times_observed"] + len(events),
                first_observed=datetime.fromisoformat(existing["first_observed"]),
                last_observed=now,
            )
        else:
            # Create new pattern
            genome_id = str(uuid.uuid4())
            try:
                typical_classification = BotClassification(
                    data.get("typical_classification", "scanner")
                )
            except ValueError:
                typical_classification = BotClassification.SCANNER
                
            try:
                typical_threat_level = ThreatLevel(
                    data.get("typical_threat_level", "medium")
                )
            except ValueError:
                typical_threat_level = ThreatLevel.MEDIUM
            
            conn.execute(
                """
                INSERT INTO threat_genome (
                    genome_id, pattern_name, pattern_description,
                    path_patterns, header_patterns, timing_signature,
                    typical_classification, typical_threat_level,
                    effective_actions, times_observed,
                    first_observed, last_observed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    genome_id,
                    pattern_name,
                    data.get("pattern_description", ""),
                    json.dumps(data.get("path_patterns", [])),
                    json.dumps(data.get("header_patterns", {})),
                    json.dumps(data.get("timing_signature", {})),
                    typical_classification.value,
                    typical_threat_level.value,
                    json.dumps(data.get("recommended_actions", [])),
                    len(events),
                    now.isoformat(),
                    now.isoformat(),
                )
            )
            conn.commit()
            
            return ThreatGenome(
                genome_id=genome_id,
                pattern_name=pattern_name,
                pattern_description=data.get("pattern_description", ""),
                path_patterns=data.get("path_patterns", []),
                header_patterns=data.get("header_patterns", {}),
                timing_signature=data.get("timing_signature", {}),
                typical_classification=typical_classification,
                typical_threat_level=typical_threat_level,
                effective_actions=[
                    AdaptiveAction(a) for a in data.get("recommended_actions", [])
                    if a in [e.value for e in AdaptiveAction]
                ],
                times_observed=len(events),
                first_observed=now,
                last_observed=now,
            )


def record_response_outcome(
    response_id: str,
    effective: bool,
    notes: str | None = None,
) -> None:
    """
    Record the outcome of an adaptive response for learning.
    
    This feedback is used to evolve defense strategies.
    """
    now = datetime.now(timezone.utc)
    with _db() as conn:
        conn.execute(
            """
            UPDATE adaptive_responses SET
                outcome_effective = ?,
                outcome_notes = ?,
                evaluated_at = ?
            WHERE response_id = ?
            """,
            (effective, notes, now.isoformat(), response_id)
        )
        
        # Update genome effectiveness if linked
        response = conn.execute(
            "SELECT * FROM adaptive_responses WHERE response_id = ?",
            (response_id,)
        ).fetchone()
        
        if response:
            action = response["action"]
            # Update genome with effective/ineffective action
            if effective:
                conn.execute(
                    """
                    UPDATE threat_genome SET
                        effective_actions = json_insert(
                            CASE WHEN effective_actions IS NULL THEN '[]' 
                            ELSE effective_actions END,
                            '$[#]', ?
                        )
                    WHERE genome_id IN (
                        SELECT genome_id FROM threat_genome 
                        WHERE effective_actions NOT LIKE ?
                        LIMIT 1
                    )
                    """,
                    (action, f'%"{action}"%')
                )
        
        conn.commit()


def save_adaptive_response(response: AdaptiveResponse) -> None:
    """Save an adaptive response for tracking and learning."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO adaptive_responses (
                response_id, fingerprint_id, action, reasoning,
                confidence, strategy_id, control_group, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                response.response_id,
                response.fingerprint_id,
                response.action.value,
                response.reasoning,
                response.confidence,
                response.strategy_id,
                response.control_group,
                response.created_at.isoformat(),
            )
        )
        conn.commit()


async def evolve_strategies() -> dict[str, Any]:
    """
    Analyze past responses and evolve defense strategies.
    
    This is the organism's adaptation mechanism.
    """
    with _db() as conn:
        # Get strategy effectiveness data
        strategy_data = conn.execute(
            """
            SELECT action, 
                   COUNT(*) as total,
                   SUM(CASE WHEN outcome_effective = 1 THEN 1 ELSE 0 END) as successful,
                   AVG(confidence) as avg_confidence
            FROM adaptive_responses
            WHERE outcome_effective IS NOT NULL
            GROUP BY action
            """
        ).fetchall()
        
        strategy_summary = [
            {
                "action": row["action"],
                "total_uses": row["total"],
                "successful": row["successful"],
                "effectiveness": row["successful"] / row["total"] if row["total"] > 0 else 0,
                "avg_confidence": row["avg_confidence"],
            }
            for row in strategy_data
        ]
        
        # Get recent patterns
        patterns = conn.execute(
            """
            SELECT pattern_name, times_observed, typical_classification,
                   typical_threat_level, effective_actions
            FROM threat_genome
            ORDER BY last_observed DESC
            LIMIT 20
            """
        ).fetchall()
        
        pattern_summary = [
            {
                "pattern": row["pattern_name"],
                "observations": row["times_observed"],
                "classification": row["typical_classification"],
                "threat_level": row["typical_threat_level"],
            }
            for row in patterns
        ]
        
        # Get recent outcomes
        outcomes = conn.execute(
            """
            SELECT action, outcome_effective, outcome_notes
            FROM adaptive_responses
            WHERE evaluated_at IS NOT NULL
            ORDER BY evaluated_at DESC
            LIMIT 50
            """
        ).fetchall()
        
        outcome_summary = [
            {
                "action": row["action"],
                "effective": bool(row["outcome_effective"]),
                "notes": row["outcome_notes"],
            }
            for row in outcomes
        ]
    
    # Ask AI to suggest improvements
    response = await _get_client().chat.completions.create(
        model="sovereign-lite",
        messages=[
            {
                "role": "system",
                "content": _STRATEGY_EVOLUTION_PROMPT.format(
                    strategy_data=json.dumps(strategy_summary),
                    pattern_data=json.dumps(pattern_summary),
                    outcome_data=json.dumps(outcome_summary),
                )
            },
            {"role": "user", "content": "Evolve our defense strategies."},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    
    return json.loads(response.choices[0].message.content)


def get_genome_patterns(limit: int = 50) -> list[ThreatGenome]:
    """Get threat patterns from the genome."""
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM threat_genome
            ORDER BY times_observed DESC, last_observed DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        return [
            ThreatGenome(
                genome_id=row["genome_id"],
                pattern_name=row["pattern_name"],
                pattern_description=row["pattern_description"] or "",
                path_patterns=json.loads(row["path_patterns"]),
                header_patterns=json.loads(row["header_patterns"]),
                timing_signature=json.loads(row["timing_signature"]),
                typical_classification=BotClassification(
                    row["typical_classification"] or "scanner"
                ),
                typical_threat_level=ThreatLevel(
                    row["typical_threat_level"] or "medium"
                ),
                effective_actions=[
                    AdaptiveAction(a) for a in json.loads(row["effective_actions"] or "[]")
                    if a in [e.value for e in AdaptiveAction]
                ],
                ineffective_actions=[
                    AdaptiveAction(a) for a in json.loads(row["ineffective_actions"] or "[]")
                    if a in [e.value for e in AdaptiveAction]
                ],
                times_observed=row["times_observed"],
                first_observed=datetime.fromisoformat(row["first_observed"]),
                last_observed=datetime.fromisoformat(row["last_observed"]),
            )
            for row in rows
        ]


def match_pattern(path: str, headers: dict[str, str]) -> ThreatGenome | None:
    """
    Match an incoming request against known threat patterns.
    
    This is the organism's immune recognition.
    """
    import re
    
    patterns = get_genome_patterns()
    
    for genome in patterns:
        # Check path patterns
        for pattern in genome.path_patterns:
            try:
                if re.search(pattern, path, re.IGNORECASE):
                    return genome
            except re.error:
                continue
        
        # Check header patterns
        for header, header_pattern in genome.header_patterns.items():
            header_value = headers.get(header, "")
            try:
                if re.search(header_pattern, header_value, re.IGNORECASE):
                    return genome
            except re.error:
                continue
    
    return None
