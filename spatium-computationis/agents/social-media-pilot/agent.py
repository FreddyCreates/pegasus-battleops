"""
Agent: Social Media Pilot 📱
Role: Generate social media content, schedules, and engagement strategies.

Provides:
- Social media post generation (multi-platform)
- Content calendar and scheduling
- Hashtag strategy
- Platform-specific content adaptation
- Engagement and growth recommendations

Glyph: 📱 (social media)
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
    agent_name="social-media-pilot",
    agent_class="SocialMediaPilot",
    version="1.0.0",
    glyph="📱",
    description="Social media — posts, schedules, hashtags, engagement strategy",
    primary_region="marketing",
    capabilities=[
        AgentCapability(
            capability_id="smp-post-generation",
            capability_type=CapabilityType.GENERATION,
            name="Social Post Generation",
            description="Generate social media posts for multiple platforms",
            input_types=["topic", "platform", "tone"],
            output_types=["social_posts"],
        ),
        AgentCapability(
            capability_id="smp-content-calendar",
            capability_type=CapabilityType.GENERATION,
            name="Social Content Calendar",
            description="Create social media content calendars",
            input_types=["domain_name", "duration", "platforms"],
            output_types=["content_calendar"],
        ),
        AgentCapability(
            capability_id="smp-hashtag-strategy",
            capability_type=CapabilityType.ANALYSIS,
            name="Hashtag Strategy",
            description="Research and recommend hashtag strategies",
            input_types=["industry", "content_themes"],
            output_types=["hashtag_recommendations"],
        ),
        AgentCapability(
            capability_id="smp-engagement-analysis",
            capability_type=CapabilityType.ANALYSIS,
            name="Engagement Analysis",
            description="Analyze engagement patterns and recommend improvements",
            input_types=["platform_data", "content_performance"],
            output_types=["engagement_recommendations"],
        ),
    ],
    requires_openai=True,
    features={"multi_platform": True, "visual_suggestions": True, "scheduling": True},
)


def _register() -> None:
    register_agent(AGENT_CONFIG)


# ---------------------------------------------------------------------------
# Core Agent Logic
# ---------------------------------------------------------------------------

_client: AsyncOpenAI | None = None
_store: MarketingStore | None = None

SUPPORTED_PLATFORMS = ["instagram", "facebook", "twitter", "linkedin", "tiktok", "pinterest"]


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


SOCIAL_SYSTEM_PROMPT = """You are an expert social media manager and content creator. 
You understand platform-specific best practices, optimal posting times, and engagement 
strategies for each major social platform.

Always return structured JSON responses with platform-specific adaptations."""


async def generate_posts(
    domain: str, topic: str, platforms: list[str], tone: str = "engaging"
) -> dict[str, Any]:
    """Generate social media posts adapted for each platform."""
    client = _get_client()
    valid_platforms = [p for p in platforms if p in SUPPORTED_PLATFORMS]

    prompt = f"""Generate social media posts for:
- Domain/Brand: {domain}
- Topic: {topic}
- Platforms: {', '.join(valid_platforms)}
- Tone: {tone}

Return a JSON object with:
- posts: array of objects, each with:
  - platform: platform name
  - content: the post text (respecting platform character limits)
  - hashtags: recommended hashtags
  - media_suggestion: what visual/media to pair with it
  - best_time: recommended posting time
  - engagement_hook: element designed to drive engagement"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SOCIAL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    content = response.choices[0].message.content
    store = _get_store()
    store.create_content_asset(
        asset_type="social_post",
        title=f"Social Posts: {topic}",
        content=content,
        domain=domain,
        metadata={"platforms": valid_platforms, "tone": tone},
    )

    return {"domain": domain, "topic": topic, "posts": content}


async def create_content_calendar(
    domain: str, platforms: list[str], duration_weeks: int = 4, posts_per_week: int = 5
) -> dict[str, Any]:
    """Create a social media content calendar."""
    client = _get_client()

    prompt = f"""Create a {duration_weeks}-week social media content calendar for:
- Domain/Brand: {domain}
- Platforms: {', '.join(platforms)}
- Posts per week: {posts_per_week}

Return a JSON object with:
- calendar: array of weeks, each with:
  - week_number: week number
  - theme: weekly content theme
  - posts: array of planned posts with day, platform, content_type, topic, caption_draft
- content_pillars: recurring content themes
- special_dates: relevant dates/events to leverage
- posting_schedule: optimal posting times per platform"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SOCIAL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    return {
        "domain": domain,
        "duration_weeks": duration_weeks,
        "calendar": response.choices[0].message.content,
    }


async def research_hashtags(
    domain: str, industry: str, content_themes: list[str]
) -> dict[str, Any]:
    """Research and recommend hashtag strategies."""
    client = _get_client()

    prompt = f"""Research hashtag strategy for:
- Domain/Brand: {domain}
- Industry: {industry}
- Content Themes: {', '.join(content_themes)}

Return a JSON object with:
- branded_hashtags: custom brand hashtags to create
- industry_hashtags: popular industry hashtags (with estimated reach)
- niche_hashtags: smaller, targeted hashtags (higher engagement rate)
- trending_relevant: currently trending relevant tags
- hashtag_sets: pre-built sets of 20-30 hashtags for different content types
- avoid: hashtags to avoid and why
- strategy_tips: platform-specific hashtag best practices"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SOCIAL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.6,
    )

    return {
        "domain": domain,
        "industry": industry,
        "hashtag_strategy": response.choices[0].message.content,
    }


async def analyze_engagement(
    domain: str, platform: str, content_performance: dict[str, Any]
) -> dict[str, Any]:
    """Analyze engagement patterns and recommend improvements."""
    client = _get_client()

    prompt = f"""Analyze social media engagement for:
- Domain/Brand: {domain}
- Platform: {platform}
- Performance Data: {content_performance}

Return a JSON object with:
- engagement_score: overall engagement assessment (0-100)
- top_performing: what content types perform best
- underperforming: what's not working and why
- audience_insights: when audience is most active
- content_recommendations: specific content changes to boost engagement
- growth_tactics: 5 specific tactics to grow the audience
- competitor_benchmarks: typical engagement rates for the industry"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SOCIAL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.5,
    )

    return {
        "domain": domain,
        "platform": platform,
        "engagement_analysis": response.choices[0].message.content,
    }


async def run(request: dict[str, Any]) -> dict[str, Any]:
    """Main entry point for the social media pilot agent."""
    action = request.get("action", "")
    domain = request.get("domain", "")

    if action == "generate_posts":
        return await generate_posts(
            domain=domain,
            topic=request.get("topic", ""),
            platforms=request.get("platforms", ["instagram", "twitter", "linkedin"]),
            tone=request.get("tone", "engaging"),
        )
    elif action == "content_calendar":
        return await create_content_calendar(
            domain=domain,
            platforms=request.get("platforms", ["instagram", "twitter", "linkedin"]),
            duration_weeks=request.get("duration_weeks", 4),
            posts_per_week=request.get("posts_per_week", 5),
        )
    elif action == "hashtag_research":
        return await research_hashtags(
            domain=domain,
            industry=request.get("industry", ""),
            content_themes=request.get("content_themes", []),
        )
    elif action == "analyze_engagement":
        return await analyze_engagement(
            domain=domain,
            platform=request.get("platform", "instagram"),
            content_performance=request.get("content_performance", {}),
        )
    else:
        return {"error": f"Unknown action: {action}"}
