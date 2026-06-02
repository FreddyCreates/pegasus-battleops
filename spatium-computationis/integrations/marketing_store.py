"""
Marketing Data Store — Campaign history, content assets, and analytics persistence.

Provides structured storage for all marketing-related data used by the
GoDaddy marketing agents platform.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).parent.parent / "field" / "marketing.db"


@dataclass
class Campaign:
    """Marketing campaign record."""
    campaign_id: str
    name: str
    status: str  # draft, active, paused, completed
    campaign_type: str  # email, social, seo, ppc, content
    domain: str
    start_date: str | None = None
    end_date: str | None = None
    budget_cents: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class ContentAsset:
    """Content asset record (blog post, landing page, email, etc.)."""
    asset_id: str
    campaign_id: str | None
    asset_type: str  # blog_post, landing_page, email, social_post, meta_description
    title: str
    content: str
    status: str  # draft, review, published, archived
    domain: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class AnalyticsSnapshot:
    """Analytics data point."""
    snapshot_id: str
    domain: str
    metric_type: str  # traffic, conversion, engagement, ranking
    metric_name: str
    metric_value: float
    dimensions: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = ""


class MarketingStore:
    """
    Persistent storage for marketing campaigns, content assets, and analytics.
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the marketing database tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id   TEXT PRIMARY KEY,
                    name          TEXT NOT NULL,
                    status        TEXT DEFAULT 'draft',
                    campaign_type TEXT NOT NULL,
                    domain        TEXT NOT NULL,
                    start_date    TEXT,
                    end_date      TEXT,
                    budget_cents  INTEGER DEFAULT 0,
                    metadata      TEXT DEFAULT '{}',
                    created_at    TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_assets (
                    asset_id      TEXT PRIMARY KEY,
                    campaign_id   TEXT,
                    asset_type    TEXT NOT NULL,
                    title         TEXT NOT NULL,
                    content       TEXT NOT NULL,
                    status        TEXT DEFAULT 'draft',
                    domain        TEXT NOT NULL,
                    metadata      TEXT DEFAULT '{}',
                    created_at    TEXT NOT NULL,
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_snapshots (
                    snapshot_id   TEXT PRIMARY KEY,
                    domain        TEXT NOT NULL,
                    metric_type   TEXT NOT NULL,
                    metric_name   TEXT NOT NULL,
                    metric_value  REAL NOT NULL,
                    dimensions    TEXT DEFAULT '{}',
                    recorded_at   TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_camp_domain ON campaigns(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_camp_status ON campaigns(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_domain ON content_assets(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_type ON content_assets(asset_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_as_domain ON analytics_snapshots(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_as_metric ON analytics_snapshots(metric_type)")
            conn.commit()

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Campaigns
    # -----------------------------------------------------------------------

    def create_campaign(self, name: str, campaign_type: str, domain: str, **kwargs: Any) -> Campaign:
        """Create a new marketing campaign."""
        campaign = Campaign(
            campaign_id=str(uuid.uuid4()),
            name=name,
            status=kwargs.get("status", "draft"),
            campaign_type=campaign_type,
            domain=domain,
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            budget_cents=kwargs.get("budget_cents", 0),
            metadata=kwargs.get("metadata", {}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO campaigns (campaign_id, name, status, campaign_type, domain,
                    start_date, end_date, budget_cents, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign.campaign_id, campaign.name, campaign.status,
                    campaign.campaign_type, campaign.domain, campaign.start_date,
                    campaign.end_date, campaign.budget_cents,
                    json.dumps(campaign.metadata), campaign.created_at,
                ),
            )
            conn.commit()
        return campaign

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        """Get a campaign by ID."""
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()
            if row:
                return Campaign(
                    campaign_id=row["campaign_id"],
                    name=row["name"],
                    status=row["status"],
                    campaign_type=row["campaign_type"],
                    domain=row["domain"],
                    start_date=row["start_date"],
                    end_date=row["end_date"],
                    budget_cents=row["budget_cents"],
                    metadata=json.loads(row["metadata"]),
                    created_at=row["created_at"],
                )
        return None

    def list_campaigns(self, domain: str | None = None, status: str | None = None) -> list[Campaign]:
        """List campaigns with optional filters."""
        query = "SELECT * FROM campaigns WHERE 1=1"
        params: list[Any] = []
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        with self._db() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                Campaign(
                    campaign_id=r["campaign_id"],
                    name=r["name"],
                    status=r["status"],
                    campaign_type=r["campaign_type"],
                    domain=r["domain"],
                    start_date=r["start_date"],
                    end_date=r["end_date"],
                    budget_cents=r["budget_cents"],
                    metadata=json.loads(r["metadata"]),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def update_campaign_status(self, campaign_id: str, status: str) -> None:
        """Update a campaign's status."""
        with self._db() as conn:
            conn.execute(
                "UPDATE campaigns SET status = ? WHERE campaign_id = ?",
                (status, campaign_id),
            )
            conn.commit()

    # -----------------------------------------------------------------------
    # Content Assets
    # -----------------------------------------------------------------------

    def create_content_asset(
        self, asset_type: str, title: str, content: str, domain: str, **kwargs: Any
    ) -> ContentAsset:
        """Create a new content asset."""
        asset = ContentAsset(
            asset_id=str(uuid.uuid4()),
            campaign_id=kwargs.get("campaign_id"),
            asset_type=asset_type,
            title=title,
            content=content,
            status=kwargs.get("status", "draft"),
            domain=domain,
            metadata=kwargs.get("metadata", {}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO content_assets (asset_id, campaign_id, asset_type, title,
                    content, status, domain, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.asset_id, asset.campaign_id, asset.asset_type,
                    asset.title, asset.content, asset.status, asset.domain,
                    json.dumps(asset.metadata), asset.created_at,
                ),
            )
            conn.commit()
        return asset

    def list_content_assets(self, domain: str | None = None, asset_type: str | None = None) -> list[ContentAsset]:
        """List content assets with optional filters."""
        query = "SELECT * FROM content_assets WHERE 1=1"
        params: list[Any] = []
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if asset_type:
            query += " AND asset_type = ?"
            params.append(asset_type)
        query += " ORDER BY created_at DESC"

        with self._db() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                ContentAsset(
                    asset_id=r["asset_id"],
                    campaign_id=r["campaign_id"],
                    asset_type=r["asset_type"],
                    title=r["title"],
                    content=r["content"],
                    status=r["status"],
                    domain=r["domain"],
                    metadata=json.loads(r["metadata"]),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    def record_metric(
        self, domain: str, metric_type: str, metric_name: str, metric_value: float, **kwargs: Any
    ) -> AnalyticsSnapshot:
        """Record an analytics metric."""
        snapshot = AnalyticsSnapshot(
            snapshot_id=str(uuid.uuid4()),
            domain=domain,
            metric_type=metric_type,
            metric_name=metric_name,
            metric_value=metric_value,
            dimensions=kwargs.get("dimensions", {}),
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO analytics_snapshots (snapshot_id, domain, metric_type,
                    metric_name, metric_value, dimensions, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id, snapshot.domain, snapshot.metric_type,
                    snapshot.metric_name, snapshot.metric_value,
                    json.dumps(snapshot.dimensions), snapshot.recorded_at,
                ),
            )
            conn.commit()
        return snapshot

    def get_metrics(
        self, domain: str, metric_type: str | None = None, limit: int = 100
    ) -> list[AnalyticsSnapshot]:
        """Get analytics metrics for a domain."""
        query = "SELECT * FROM analytics_snapshots WHERE domain = ?"
        params: list[Any] = [domain]
        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type)
        query += " ORDER BY recorded_at DESC LIMIT ?"
        params.append(limit)

        with self._db() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                AnalyticsSnapshot(
                    snapshot_id=r["snapshot_id"],
                    domain=r["domain"],
                    metric_type=r["metric_type"],
                    metric_name=r["metric_name"],
                    metric_value=r["metric_value"],
                    dimensions=json.loads(r["dimensions"]),
                    recorded_at=r["recorded_at"],
                )
                for r in rows
            ]
