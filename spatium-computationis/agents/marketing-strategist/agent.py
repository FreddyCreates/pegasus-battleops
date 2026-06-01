"""
Agent: Marketing Strategist 📊
Role: Generate marketing plans, campaign calendars, and strategic recommendations.

Provides:
- Marketing plan generation
- Campaign calendar creation
- Audience targeting and segmentation
- Budget allocation recommendations
- Competitive analysis summaries

Glyph: 📊 (strategy and data)
Capabilities: GENERATION, ANALYSIS
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
    agent_name="marketing-strategist",
    agent_class="MarketingStrategist",
    version="1.0.0",
    glyph="📊",
    description="Marketing strategy — plans, campaigns, audience targeting, budgets",
    primary_region="marketing",
    capabilities=[
        AgentCapability(
            capability_id="ms-plan-generation",
            capability_type=CapabilityType.GENERATION,
            name="Marketing Plan Generation",
            description="Generate comprehensive marketing plans for domains",
            input_types=["domain_name", "business_context", "goals"],
            output_types=["marketing_plan"],
        ),
        AgentCapability(
            capability_id="ms-campaign-calendar",
            capability_type=CapabilityType.GENERATION,
            name="Campaign Calendar",
            description="Create campaign calendars with timelines and milestones",
            input_types=["domain_name", "date_range", "campaign_type"],
            output_types=["campaign_calendar"],
        ),
        AgentCapability(
            capability_id="ms-audience-analysis",
            capability_type=CapabilityType.ANALYSIS,
            name="Audience Analysis",
            description="Analyze and segment target audiences",
            input_types=["business_context", "current_data"],
            output_types=["audience_segments", "targeting_recommendations"],
        ),
        AgentCapability(
            capability_id="ms-budget-allocation",
            capability_type=CapabilityType.ANALYSIS,
            name="Budget Allocation",
            description="Recommend budget allocation across marketing channels",
            input_types=["total_budget", "goals", "current_performance"],
            output_types=["budget_plan"],
        ),
    ],
    requires_openai=True,
    features={"ai_planning": True, "competitive_analysis": True},
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


STRATEGY_SYSTEM_PROMPT = """You are an expert digital marketing strategist specializing in 
website marketing for small-to-medium businesses using GoDaddy. You create actionable, 
data-driven marketing plans and campaign strategies.

Always structure your responses as JSON with clear sections. Be specific with timelines, 
channels, and measurable KPIs."""


async def generate_marketing_plan(
    domain: str, business_context: str, goals: list[str], budget_cents: int = 0
) -> dict[str, Any]:
    """Generate a comprehensive marketing plan."""
    client = _get_client()

    prompt = f"""Create a marketing plan for:
- Domain: {domain}
- Business: {business_context}
- Goals: {', '.join(goals)}
- Monthly Budget: ${budget_cents / 100:.2f}

Return a JSON object with:
- executive_summary: brief overview
- target_audience: audience segments
- channels: recommended marketing channels with allocation %
- timeline: 90-day roadmap with milestones
- kpis: measurable KPIs for each goal
- quick_wins: 3-5 immediate actions"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    plan = response.choices[0].message.content
    store = _get_store()
    campaign = store.create_campaign(
        name=f"Marketing Plan - {domain}",
        campaign_type="strategic_plan",
        domain=domain,
        budget_cents=budget_cents,
        metadata={"goals": goals, "business_context": business_context},
    )

    return {
        "campaign_id": campaign.campaign_id,
        "domain": domain,
        "plan": plan,
    }


async def create_campaign_calendar(
    domain: str, campaign_type: str, duration_days: int = 90
) -> dict[str, Any]:
    """Create a campaign calendar with timeline and milestones."""
    client = _get_client()

    prompt = f"""Create a {duration_days}-day campaign calendar for:
- Domain: {domain}
- Campaign Type: {campaign_type}

Return a JSON object with:
- phases: array of phases, each with name, start_day, end_day, activities
- milestones: key dates and deliverables
- content_schedule: what content to publish and when
- review_points: dates for performance review"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    return {
        "domain": domain,
        "campaign_type": campaign_type,
        "duration_days": duration_days,
        "calendar": response.choices[0].message.content,
    }


async def analyze_audience(domain: str, business_context: str) -> dict[str, Any]:
    """Analyze and segment target audiences."""
    client = _get_client()

    prompt = f"""Analyze the target audience for:
- Domain: {domain}
- Business: {business_context}

Return a JSON object with:
- primary_segments: array of audience segments with demographics, psychographics, pain_points
- targeting_recommendations: platform-specific targeting suggestions
- messaging_themes: key messages that resonate with each segment
- channels_by_segment: best channels to reach each segment"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    return {
        "domain": domain,
        "audience_analysis": response.choices[0].message.content,
    }


async def recommend_budget_allocation(
    domain: str, total_budget_cents: int, goals: list[str]
) -> dict[str, Any]:
    """Recommend budget allocation across marketing channels."""
    client = _get_client()

    prompt = f"""Recommend budget allocation for:
- Domain: {domain}
- Total Monthly Budget: ${total_budget_cents / 100:.2f}
- Goals: {', '.join(goals)}

Return a JSON object with:
- allocations: array of channel, percentage, amount_cents, rationale
- expected_roi: estimated ROI per channel
- minimum_viable: minimum budget needed per channel to be effective
- scaling_plan: how to scale if budget increases"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    return {
        "domain": domain,
        "total_budget_cents": total_budget_cents,
        "budget_plan": response.choices[0].message.content,
    }


async def run(request: dict[str, Any]) -> dict[str, Any]:
    """Main entry point for the marketing strategist agent."""
    action = request.get("action", "")
    domain = request.get("domain", "")

    if action == "generate_plan":
        return await generate_marketing_plan(
            domain=domain,
            business_context=request.get("business_context", ""),
            goals=request.get("goals", []),
            budget_cents=request.get("budget_cents", 0),
        )
    elif action == "campaign_calendar":
        return await create_campaign_calendar(
            domain=domain,
            campaign_type=request.get("campaign_type", "general"),
            duration_days=request.get("duration_days", 90),
        )
    elif action == "analyze_audience":
        return await analyze_audience(
            domain=domain,
            business_context=request.get("business_context", ""),
        )
    elif action == "budget_allocation":
        return await recommend_budget_allocation(
            domain=domain,
            total_budget_cents=request.get("budget_cents", 100000),
            goals=request.get("goals", []),
        )
    else:
        return {"error": f"Unknown action: {action}"}
