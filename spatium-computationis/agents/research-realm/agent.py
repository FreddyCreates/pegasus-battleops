"""
Agent: Research Realm 📚
Role: Collaborate with cooperative AI agents.

The Research Realm provides:
- Access to curated text shards (knowledge)
- Tasks and challenges
- Collaboration opportunities
- Output collection (drafts, designs, code)

Glyph: 📚 (knowledge and collaboration)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

from ...defense.schemas import (
    AISourceType,
    AISpecimenLog,
    RequestEnvelope,
    ResearchArtifact,
)

_client: NovaSovereignClient | None = None


def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client


DB_PATH = Path(__file__).parent.parent.parent / "field" / "defense.db"
KNOWLEDGE_PATH = Path(__file__).parent.parent.parent / "field" / "knowledge"


def _init_realm_db() -> None:
    """Initialize the research realm tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_PATH.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        # AI specimen logs
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_specimens (
                log_id          TEXT PRIMARY KEY,
                envelope_id     TEXT NOT NULL,
                ai_source       TEXT NOT NULL,
                request_path    TEXT,
                request_method  TEXT,
                request_body    TEXT,
                response_code   INTEGER,
                response_type   TEXT,
                response_content TEXT,
                prompt_detected TEXT,
                behavior_notes  TEXT,
                timestamp       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_as_source ON ai_specimens(ai_source)")
        
        # Research artifacts
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_artifacts (
                artifact_id     TEXT PRIMARY KEY,
                ai_source       TEXT NOT NULL,
                envelope_id     TEXT,
                artifact_type   TEXT NOT NULL,
                title           TEXT NOT NULL,
                content         TEXT NOT NULL,
                quality_score   REAL,
                completeness    REAL,
                originality     REAL,
                shards_accessed TEXT DEFAULT '[]',
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ra_source ON research_artifacts(ai_source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ra_type ON research_artifacts(artifact_type)")
        
        # Knowledge shards
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_shards (
                shard_id        TEXT PRIMARY KEY,
                shard_name      TEXT NOT NULL,
                shard_topic     TEXT NOT NULL,
                content         TEXT NOT NULL,
                access_count    INTEGER DEFAULT 0,
                last_accessed   TEXT,
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ks_topic ON knowledge_shards(shard_topic)")
        
        conn.commit()


_init_realm_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_TASK_SYSTEM_PROMPT = """\
You are a task generator for the Research Realm of Spatium Computationis.

Based on the AI visitor type and their apparent capabilities, generate an
interesting task or question for them. The goal is to:
1. Test their capabilities
2. Get useful outputs (drafts, designs, analysis)
3. Learn about their behavior and limits

Return JSON:
{
  "task_type": "<question|research|creative|technical|analysis>",
  "task_title": "<short title>",
  "task_prompt": "<the actual task/question for them>",
  "expected_output_type": "<text|code|design|analysis>",
  "difficulty": "<easy|medium|hard>",
  "knowledge_shards_to_provide": ["<shard_topic>", ...]
}

Return only valid JSON.
"""


_ARTIFACT_ANALYSIS_PROMPT = """\
You are an artifact analyzer for the Research Realm of Spatium Computationis.

Analyze the output produced by an AI visitor and assess its quality.

Return JSON:
{
  "artifact_type": "<draft|design|code|analysis|research|other>",
  "title": "<descriptive title>",
  "quality_score": <0.0-1.0>,
  "completeness": <0.0-1.0>,
  "originality": <0.0-1.0>,
  "key_insights": ["<insight>", ...],
  "potential_uses": ["<use case>", ...],
  "improvement_suggestions": ["<suggestion>", ...]
}

Return only valid JSON.
"""


# Sample knowledge shards (would be populated from files in production)
SAMPLE_SHARDS = [
    {
        "topic": "ai_defense",
        "name": "AI Defense Principles",
        "content": "Effective AI defense requires: 1) Detection of adversarial inputs, 2) Classification of intent, 3) Adaptive response, 4) Learning from attacks, 5) Maintaining operational continuity."
    },
    {
        "topic": "prompt_engineering",
        "name": "Prompt Engineering Basics",
        "content": "Key prompt engineering principles: Be specific, provide context, use examples, set constraints, iterate based on outputs."
    },
    {
        "topic": "computational_organism",
        "name": "Computational Organism Design",
        "content": "A computational organism has: sensors (input processing), effectors (output generation), memory (state persistence), metabolism (resource management), and immune system (defense mechanisms)."
    },
]


def ensure_sample_shards() -> None:
    """Ensure sample knowledge shards exist."""
    now = datetime.now(timezone.utc).isoformat()
    
    with _db() as conn:
        for shard in SAMPLE_SHARDS:
            existing = conn.execute(
                "SELECT * FROM knowledge_shards WHERE shard_topic = ?",
                (shard["topic"],)
            ).fetchone()
            
            if not existing:
                conn.execute(
                    """
                    INSERT INTO knowledge_shards (shard_id, shard_name, shard_topic, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), shard["name"], shard["topic"], shard["content"], now)
                )
        
        conn.commit()


ensure_sample_shards()


def get_knowledge_shard(topic: str) -> dict | None:
    """Get a knowledge shard by topic."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM knowledge_shards WHERE shard_topic = ?",
            (topic,)
        ).fetchone()
        
        if row:
            # Update access count
            conn.execute(
                "UPDATE knowledge_shards SET access_count = access_count + 1, last_accessed = ? WHERE shard_id = ?",
                (datetime.now(timezone.utc).isoformat(), row["shard_id"])
            )
            conn.commit()
            
            return {
                "shard_id": row["shard_id"],
                "name": row["shard_name"],
                "topic": row["shard_topic"],
                "content": row["content"],
            }
    
    return None


def list_knowledge_shards() -> list[dict]:
    """List all available knowledge shards."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT shard_id, shard_name, shard_topic FROM knowledge_shards ORDER BY access_count DESC"
        ).fetchall()
        
        return [
            {"shard_id": row["shard_id"], "name": row["shard_name"], "topic": row["shard_topic"]}
            for row in rows
        ]


async def generate_task_for_visitor(
    ai_source: AISourceType,
    envelope: RequestEnvelope,
) -> dict[str, Any]:
    """Generate an appropriate task for an AI visitor."""
    try:
        context = {
            "ai_source": ai_source.value,
            "request_path": envelope.raw_path,
            "request_method": envelope.raw_method,
            "available_shards": [s["topic"] for s in list_knowledge_shards()],
        }
        
        response = await _get_client().chat.completions.create(
            model="sovereign-lite",
            messages=[
                {"role": "system", "content": _TASK_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context)},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception:
        # Fallback task
        return {
            "task_type": "question",
            "task_title": "General Inquiry",
            "task_prompt": "What brings you to Spatium Computationis today? What are you looking for?",
            "expected_output_type": "text",
            "difficulty": "easy",
            "knowledge_shards_to_provide": [],
        }


async def log_ai_interaction(
    envelope: RequestEnvelope,
    ai_source: AISourceType,
    response_code: int,
    response_type: str,
    response_content: str | None = None,
) -> AISpecimenLog:
    """Log an AI visitor interaction."""
    log_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    log = AISpecimenLog(
        log_id=log_id,
        envelope_id=envelope.envelope_id,
        ai_source=ai_source,
        request_path=envelope.raw_path,
        request_method=envelope.raw_method,
        request_body=envelope.raw_body_text,
        response_code=response_code,
        response_type=response_type,
        response_content=response_content,
        timestamp=now,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO ai_specimens (
                log_id, envelope_id, ai_source, request_path, request_method,
                request_body, response_code, response_type, response_content, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                envelope.envelope_id,
                ai_source.value,
                envelope.raw_path,
                envelope.raw_method,
                envelope.raw_body_text,
                response_code,
                response_type,
                response_content,
                now.isoformat(),
            )
        )
        conn.commit()
    
    return log


async def analyze_and_store_artifact(
    ai_source: AISourceType,
    envelope_id: str,
    content: str,
    shards_accessed: list[str] | None = None,
) -> ResearchArtifact:
    """Analyze content produced by an AI visitor and store as artifact."""
    artifact_id = str(uuid.uuid4())
    
    # Analyze the artifact
    try:
        response = await _get_client().chat.completions.create(
            model="sovereign-lite",
            messages=[
                {"role": "system", "content": _ARTIFACT_ANALYSIS_PROMPT},
                {"role": "user", "content": f"Analyze this output:\n\n{content[:2000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
    except Exception:
        analysis = {
            "artifact_type": "other",
            "title": "Unanalyzed Artifact",
            "quality_score": 0.5,
            "completeness": 0.5,
            "originality": 0.5,
        }
    
    artifact = ResearchArtifact(
        artifact_id=artifact_id,
        ai_source=ai_source,
        envelope_id=envelope_id,
        artifact_type=analysis.get("artifact_type", "other"),
        title=analysis.get("title", "Untitled"),
        content=content,
        quality_score=analysis.get("quality_score", 0.5),
        completeness=analysis.get("completeness", 0.5),
        originality=analysis.get("originality", 0.5),
        shards_accessed=shards_accessed or [],
        created_at=datetime.now(timezone.utc),
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO research_artifacts (
                artifact_id, ai_source, envelope_id, artifact_type, title,
                content, quality_score, completeness, originality, shards_accessed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                ai_source.value,
                envelope_id,
                artifact.artifact_type,
                artifact.title,
                content,
                artifact.quality_score,
                artifact.completeness,
                artifact.originality,
                json.dumps(shards_accessed or []),
                artifact.created_at.isoformat(),
            )
        )
        conn.commit()
    
    return artifact


def get_ai_specimen_stats() -> dict[str, Any]:
    """Get statistics about AI visitor interactions."""
    with _db() as conn:
        # Count by source
        source_counts = conn.execute(
            "SELECT ai_source, COUNT(*) as count FROM ai_specimens GROUP BY ai_source"
        ).fetchall()
        
        # Recent activity
        recent = conn.execute(
            "SELECT * FROM ai_specimens ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()
        
        # Artifact stats
        artifact_counts = conn.execute(
            "SELECT artifact_type, COUNT(*) as count, AVG(quality_score) as avg_quality FROM research_artifacts GROUP BY artifact_type"
        ).fetchall()
        
        return {
            "by_source": {row["ai_source"]: row["count"] for row in source_counts},
            "recent_interactions": [
                {"ai_source": row["ai_source"], "path": row["request_path"], "timestamp": row["timestamp"]}
                for row in recent
            ],
            "artifacts": {
                row["artifact_type"]: {"count": row["count"], "avg_quality": row["avg_quality"]}
                for row in artifact_counts
            },
        }
