"""
Agent: SEO Optimizer 🔍
Role: Keyword research, on-page SEO audits, sitemap generation, and schema markup.

Provides:
- Keyword research and recommendations
- On-page SEO audits for GoDaddy-hosted sites
- Sitemap XML generation
- Schema.org structured data suggestions
- Technical SEO recommendations

Glyph: 🔍 (search optimization)
Capabilities: ANALYSIS, GENERATION
"""

from __future__ import annotations

from typing import Any

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

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
    agent_name="seo-optimizer",
    agent_class="SEOOptimizer",
    version="1.0.0",
    glyph="🔍",
    description="SEO optimization — keywords, audits, sitemaps, schema markup",
    primary_region="marketing",
    capabilities=[
        AgentCapability(
            capability_id="seo-keyword-research",
            capability_type=CapabilityType.ANALYSIS,
            name="Keyword Research",
            description="Research and recommend target keywords",
            input_types=["domain_name", "business_context", "competitors"],
            output_types=["keyword_recommendations"],
        ),
        AgentCapability(
            capability_id="seo-page-audit",
            capability_type=CapabilityType.ANALYSIS,
            name="On-Page SEO Audit",
            description="Audit page content for SEO best practices",
            input_types=["page_url", "page_content"],
            output_types=["seo_audit_report"],
        ),
        AgentCapability(
            capability_id="seo-sitemap-generation",
            capability_type=CapabilityType.GENERATION,
            name="Sitemap Generation",
            description="Generate XML sitemaps for websites",
            input_types=["domain_name", "page_list"],
            output_types=["sitemap_xml"],
        ),
        AgentCapability(
            capability_id="seo-schema-markup",
            capability_type=CapabilityType.GENERATION,
            name="Schema Markup",
            description="Generate Schema.org structured data",
            input_types=["page_type", "business_info"],
            output_types=["schema_json_ld"],
        ),
    ],
    requires_nova_sovereign=True,
    features={"technical_seo": True, "local_seo": True, "schema_generation": True},
)


def _register() -> None:
    register_agent(AGENT_CONFIG)


# ---------------------------------------------------------------------------
# Core Agent Logic
# ---------------------------------------------------------------------------

_client: NovaSovereignClient | None = None
_store: MarketingStore | None = None


def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client


def _get_store() -> MarketingStore:
    global _store
    if _store is None:
        _store = MarketingStore()
    return _store


SEO_SYSTEM_PROMPT = """You are an expert SEO specialist with deep knowledge of search engine 
algorithms, technical SEO, and content optimization. You provide actionable, data-driven 
recommendations for improving search visibility.

Always return structured JSON responses with specific, implementable recommendations."""


async def research_keywords(
    domain: str, business_context: str, seed_keywords: list[str] | None = None
) -> dict[str, Any]:
    """Research and recommend target keywords."""
    client = _get_client()

    seeds = ", ".join(seed_keywords) if seed_keywords else "none provided"
    prompt = f"""Perform keyword research for:
- Domain: {domain}
- Business: {business_context}
- Seed Keywords: {seeds}

Return a JSON object with:
- primary_keywords: array of 5-10 main keywords with estimated difficulty (low/medium/high) and intent (informational/transactional/navigational)
- long_tail_keywords: array of 10-15 long-tail variations
- local_keywords: array of local SEO keywords if applicable
- content_clusters: groups of related keywords for content planning
- competitor_gaps: keyword opportunities competitors may be missing
- priority_order: recommended implementation order"""

    response = await client.chat.completions.create(
        model="sovereign-lite",
        messages=[
            {"role": "system", "content": SEO_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.6,
    )

    return {
        "domain": domain,
        "keyword_research": response.choices[0].message.content,
    }


async def audit_page_seo(domain: str, page_url: str, page_content: str) -> dict[str, Any]:
    """Perform an on-page SEO audit."""
    client = _get_client()

    prompt = f"""Perform an on-page SEO audit for:
- Domain: {domain}
- Page URL: {page_url}
- Content (excerpt): {page_content[:2000]}

Return a JSON object with:
- score: overall SEO score (0-100)
- title_tag: analysis and recommendation
- meta_description: analysis and recommendation
- headings: H1/H2/H3 structure analysis
- content_quality: content length, readability, keyword usage
- internal_links: recommendations
- image_optimization: alt tags, file sizes
- mobile_friendliness: assessment
- page_speed_tips: performance recommendations
- action_items: prioritized list of fixes (high/medium/low priority)"""

    response = await client.chat.completions.create(
        model="sovereign-lite",
        messages=[
            {"role": "system", "content": SEO_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    return {
        "domain": domain,
        "page_url": page_url,
        "audit_report": response.choices[0].message.content,
    }


async def generate_sitemap(domain: str, pages: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate an XML sitemap."""
    xml_entries = []
    for page in pages:
        url = page.get("url", f"https://{domain}/")
        priority = page.get("priority", "0.5")
        changefreq = page.get("changefreq", "weekly")
        xml_entries.append(
            f"  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <changefreq>{changefreq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )

    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(xml_entries)
        + "\n</urlset>"
    )

    return {
        "domain": domain,
        "sitemap_xml": sitemap_xml,
        "page_count": len(pages),
    }


async def generate_schema_markup(
    domain: str, page_type: str, business_info: dict[str, Any]
) -> dict[str, Any]:
    """Generate Schema.org structured data."""
    client = _get_client()

    prompt = f"""Generate Schema.org JSON-LD markup for:
- Domain: {domain}
- Page Type: {page_type} (e.g., homepage, product, service, article, local_business)
- Business Info: {business_info}

Return a JSON object with:
- schema_type: the Schema.org type used
- json_ld: the complete JSON-LD script content (as a nested object)
- implementation_notes: where and how to add this markup
- additional_schemas: other relevant schemas to consider"""

    response = await client.chat.completions.create(
        model="sovereign-lite",
        messages=[
            {"role": "system", "content": SEO_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    return {
        "domain": domain,
        "page_type": page_type,
        "schema_markup": response.choices[0].message.content,
    }


async def run(request: dict[str, Any]) -> dict[str, Any]:
    """Main entry point for the SEO optimizer agent."""
    action = request.get("action", "")
    domain = request.get("domain", "")

    if action == "keyword_research":
        return await research_keywords(
            domain=domain,
            business_context=request.get("business_context", ""),
            seed_keywords=request.get("seed_keywords"),
        )
    elif action == "page_audit":
        return await audit_page_seo(
            domain=domain,
            page_url=request.get("page_url", ""),
            page_content=request.get("page_content", ""),
        )
    elif action == "generate_sitemap":
        return await generate_sitemap(
            domain=domain,
            pages=request.get("pages", []),
        )
    elif action == "schema_markup":
        return await generate_schema_markup(
            domain=domain,
            page_type=request.get("page_type", "homepage"),
            business_info=request.get("business_info", {}),
        )
    else:
        return {"error": f"Unknown action: {action}"}
