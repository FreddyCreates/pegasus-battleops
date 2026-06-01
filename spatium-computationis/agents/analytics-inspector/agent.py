"""
Agent: Analytics Inspector 📈
Role: Pull website traffic/performance data and generate marketing reports.

Provides:
- Website traffic analysis
- Marketing performance reports
- Conversion tracking and funnel analysis
- Campaign ROI calculations
- Trend identification and forecasting

Glyph: 📈 (analytics and growth)
Capabilities: ANALYSIS, STORAGE
"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from ...integrations.marketing_store import MarketingStore
from ...scaffolds.base import (
    AgentCapability,
    AgentConfig,
    CapabilityType,
    register_agent,
)


# ---------------------------------------------------------------------------
# Agent Registration
# ---------------------------------------------------------------------------

AGENT_CONFIG = AgentConfig(
    agent_name="analytics-inspector",
    agent_class="AnalyticsInspector",
    version="1.0.0",
    glyph="📈",
    description="Analytics — traffic, conversions, performance reports, ROI tracking",
    primary_region="marketing",
    capabilities=[
        AgentCapability(
            capability_id="ai-traffic-analysis",
            capability_type=CapabilityType.ANALYSIS,
            name="Traffic Analysis",
            description="Analyze website traffic patterns and sources",
            input_types=["domain_name", "date_range", "traffic_data"],
            output_types=["traffic_report"],
        ),
        AgentCapability(
            capability_id="ai-performance-reports",
            capability_type=CapabilityType.ANALYSIS,
            name="Performance Reports",
            description="Generate marketing performance reports",
            input_types=["campaign_id", "metrics_data"],
            output_types=["performance_report"],
        ),
        AgentCapability(
            capability_id="ai-conversion-tracking",
            capability_type=CapabilityType.ANALYSIS,
            name="Conversion Tracking",
            description="Track and analyze conversion funnels",
            input_types=["funnel_data", "goals"],
            output_types=["conversion_analysis"],
        ),
        AgentCapability(
            capability_id="ai-data-storage",
            capability_type=CapabilityType.STORAGE,
            name="Analytics Storage",
            description="Store and retrieve analytics snapshots",
            input_types=["metrics"],
            output_types=["stored_metrics"],
        ),
    ],
    requires_openai=True,
    requires_database=True,
    features={"trend_detection": True, "forecasting": True, "roi_calculation": True},
)


def _register() -> None:
    register_agent(AGENT_CONFIG)


# ---------------------------------------------------------------------------
# Core Agent Logic
# ---------------------------------------------------------------------------

_client: AsyncOpenAI | None = None
_store: MarketingStore | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


def _get_store() -> MarketingStore:
    global _store
    if _store is None:
        _store = MarketingStore()
    return _store


ANALYTICS_SYSTEM_PROMPT = """You are an expert digital analytics specialist. You interpret 
website and marketing data to provide actionable insights. You're skilled at identifying 
trends, calculating ROI, and making data-driven recommendations.

Always return structured JSON responses with clear metrics and actionable recommendations."""


async def analyze_traffic(
    domain: str, traffic_data: dict[str, Any], date_range: str = "last_30_days"
) -> dict[str, Any]:
    """Analyze website traffic patterns and sources."""
    client = _get_client()
    store = _get_store()

    prompt = f"""Analyze website traffic for:
- Domain: {domain}
- Date Range: {date_range}
- Traffic Data: {traffic_data}

Return a JSON object with:
- summary: executive summary of traffic performance
- total_visits: total visits in period
- traffic_sources: breakdown by source (organic, paid, social, direct, referral)
- top_pages: highest traffic pages
- trends: notable trends (increasing/decreasing)
- bounce_rate_analysis: assessment of bounce rates
- geographic_insights: if available, geographic distribution
- recommendations: 3-5 actionable recommendations to improve traffic"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ANALYTICS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    # Store metrics
    if traffic_data.get("total_visits"):
        store.record_metric(
            domain=domain,
            metric_type="traffic",
            metric_name="total_visits",
            metric_value=float(traffic_data["total_visits"]),
            dimensions={"date_range": date_range},
        )

    return {
        "domain": domain,
        "date_range": date_range,
        "traffic_analysis": response.choices[0].message.content,
    }


async def generate_performance_report(
    domain: str, campaign_id: str | None = None, metrics: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Generate a marketing performance report."""
    client = _get_client()
    store = _get_store()

    # Get historical metrics
    historical = store.get_metrics(domain, limit=50)
    historical_summary = [
        {"metric": m.metric_name, "value": m.metric_value, "date": m.recorded_at}
        for m in historical[:20]
    ]

    prompt = f"""Generate a marketing performance report for:
- Domain: {domain}
- Campaign ID: {campaign_id or 'all campaigns'}
- Current Metrics: {metrics or 'not provided'}
- Historical Data: {historical_summary}

Return a JSON object with:
- report_title: report title
- period: reporting period
- kpi_summary: key performance indicators with values and trends
- channel_performance: performance by marketing channel
- campaign_highlights: top performing campaigns/content
- areas_of_concern: metrics that need attention
- month_over_month: changes from previous period
- recommendations: prioritized actions to improve performance
- forecast: projected metrics for next period"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ANALYTICS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    return {
        "domain": domain,
        "campaign_id": campaign_id,
        "performance_report": response.choices[0].message.content,
    }


async def analyze_conversions(
    domain: str, funnel_data: dict[str, Any], goals: list[str]
) -> dict[str, Any]:
    """Analyze conversion funnels."""
    client = _get_client()

    prompt = f"""Analyze conversion funnel for:
- Domain: {domain}
- Funnel Data: {funnel_data}
- Goals: {', '.join(goals)}

Return a JSON object with:
- overall_conversion_rate: total conversion rate
- funnel_stages: array of stages with visitors, drop_off_rate, conversion_to_next
- bottlenecks: where users are dropping off most
- segment_analysis: conversion by traffic source/device if available
- optimization_opportunities: specific changes to improve each stage
- ab_test_suggestions: experiments to run
- estimated_impact: potential revenue/conversion lift from recommendations"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ANALYTICS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    return {
        "domain": domain,
        "conversion_analysis": response.choices[0].message.content,
    }


async def record_metrics(domain: str, metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Store analytics metrics for tracking over time."""
    store = _get_store()
    stored = []
    for m in metrics:
        snapshot = store.record_metric(
            domain=domain,
            metric_type=m.get("type", "general"),
            metric_name=m.get("name", "unknown"),
            metric_value=float(m.get("value", 0)),
            dimensions=m.get("dimensions", {}),
        )
        stored.append(snapshot.snapshot_id)

    return {
        "domain": domain,
        "metrics_stored": len(stored),
        "snapshot_ids": stored,
    }


async def get_historical_metrics(
    domain: str, metric_type: str | None = None, limit: int = 100
) -> dict[str, Any]:
    """Retrieve historical metrics."""
    store = _get_store()
    metrics = store.get_metrics(domain, metric_type=metric_type, limit=limit)
    return {
        "domain": domain,
        "metric_type": metric_type,
        "count": len(metrics),
        "metrics": [
            {
                "name": m.metric_name,
                "value": m.metric_value,
                "type": m.metric_type,
                "recorded_at": m.recorded_at,
            }
            for m in metrics
        ],
    }


async def run(request: dict[str, Any]) -> dict[str, Any]:
    """Main entry point for the analytics inspector agent."""
    action = request.get("action", "")
    domain = request.get("domain", "")

    if action == "analyze_traffic":
        return await analyze_traffic(
            domain=domain,
            traffic_data=request.get("traffic_data", {}),
            date_range=request.get("date_range", "last_30_days"),
        )
    elif action == "performance_report":
        return await generate_performance_report(
            domain=domain,
            campaign_id=request.get("campaign_id"),
            metrics=request.get("metrics"),
        )
    elif action == "analyze_conversions":
        return await analyze_conversions(
            domain=domain,
            funnel_data=request.get("funnel_data", {}),
            goals=request.get("goals", []),
        )
    elif action == "record_metrics":
        return await record_metrics(
            domain=domain,
            metrics=request.get("metrics", []),
        )
    elif action == "get_metrics":
        return await get_historical_metrics(
            domain=domain,
            metric_type=request.get("metric_type"),
            limit=request.get("limit", 100),
        )
    else:
        return {"error": f"Unknown action: {action}"}
