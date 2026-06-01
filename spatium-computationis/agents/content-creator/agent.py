"""
Agent: Content Creator ✍️
Role: Generate website copy, blog posts, landing pages, and email sequences.

Provides:
- Website copy generation (headlines, CTAs, about pages)
- Blog post creation with SEO considerations
- Landing page content
- Email marketing templates and sequences
- Meta descriptions and titles

Glyph: ✍️ (content creation)
Capabilities: GENERATION
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
    agent_name="content-creator",
    agent_class="ContentCreator",
    version="1.0.0",
    glyph="✍️",
    description="Content generation — copy, blogs, emails, landing pages",
    primary_region="marketing",
    capabilities=[
        AgentCapability(
            capability_id="cc-website-copy",
            capability_type=CapabilityType.GENERATION,
            name="Website Copy",
            description="Generate website copy including headlines, CTAs, and page content",
            input_types=["domain_name", "page_type", "business_context"],
            output_types=["website_copy"],
        ),
        AgentCapability(
            capability_id="cc-blog-posts",
            capability_type=CapabilityType.GENERATION,
            name="Blog Posts",
            description="Create SEO-optimized blog posts",
            input_types=["topic", "keywords", "tone"],
            output_types=["blog_post"],
        ),
        AgentCapability(
            capability_id="cc-email-sequences",
            capability_type=CapabilityType.GENERATION,
            name="Email Sequences",
            description="Generate email marketing templates and drip sequences",
            input_types=["sequence_type", "audience", "goal"],
            output_types=["email_sequence"],
        ),
        AgentCapability(
            capability_id="cc-landing-pages",
            capability_type=CapabilityType.GENERATION,
            name="Landing Pages",
            description="Create conversion-optimized landing page content",
            input_types=["offer", "audience", "cta"],
            output_types=["landing_page_content"],
        ),
    ],
    requires_openai=True,
    features={"seo_aware": True, "multi_tone": True, "ab_variants": True},
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


CONTENT_SYSTEM_PROMPT = """You are an expert content creator and copywriter specializing in 
website content for small-to-medium businesses. You create compelling, conversion-focused 
copy that is also SEO-friendly.

Always return structured JSON responses. Write in a clear, engaging tone unless 
otherwise specified."""


async def generate_website_copy(
    domain: str, page_type: str, business_context: str, tone: str = "professional"
) -> dict[str, Any]:
    """Generate website copy for a specific page type."""
    client = _get_client()

    prompt = f"""Generate website copy for:
- Domain: {domain}
- Page Type: {page_type} (e.g., homepage, about, services, contact)
- Business: {business_context}
- Tone: {tone}

Return a JSON object with:
- headline: main headline (H1)
- subheadline: supporting headline
- body_sections: array of sections with heading and content
- cta_primary: primary call-to-action text
- cta_secondary: secondary CTA text
- meta_title: SEO title tag (60 chars max)
- meta_description: SEO meta description (160 chars max)"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    content = response.choices[0].message.content
    store = _get_store()
    asset = store.create_content_asset(
        asset_type="website_copy",
        title=f"{page_type.title()} - {domain}",
        content=content,
        domain=domain,
        metadata={"page_type": page_type, "tone": tone},
    )

    return {"asset_id": asset.asset_id, "domain": domain, "page_type": page_type, "copy": content}


async def generate_blog_post(
    domain: str, topic: str, keywords: list[str], word_count: int = 800
) -> dict[str, Any]:
    """Generate an SEO-optimized blog post."""
    client = _get_client()

    prompt = f"""Write a blog post:
- Domain: {domain}
- Topic: {topic}
- Target Keywords: {', '.join(keywords)}
- Target Word Count: ~{word_count} words

Return a JSON object with:
- title: engaging blog title (include primary keyword)
- meta_description: SEO meta description
- introduction: opening paragraph
- sections: array of objects with heading and content
- conclusion: closing paragraph with CTA
- tags: suggested tags/categories"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    content = response.choices[0].message.content
    store = _get_store()
    asset = store.create_content_asset(
        asset_type="blog_post",
        title=topic,
        content=content,
        domain=domain,
        metadata={"keywords": keywords, "word_count": word_count},
    )

    return {"asset_id": asset.asset_id, "domain": domain, "topic": topic, "blog_post": content}


async def generate_email_sequence(
    domain: str, sequence_type: str, audience: str, num_emails: int = 5
) -> dict[str, Any]:
    """Generate an email marketing sequence."""
    client = _get_client()

    prompt = f"""Create a {num_emails}-email sequence:
- Domain: {domain}
- Sequence Type: {sequence_type} (e.g., welcome, nurture, re-engagement, promotional)
- Target Audience: {audience}

Return a JSON object with:
- sequence_name: name for this sequence
- emails: array of objects, each with:
  - subject_line: compelling subject
  - preview_text: email preview text
  - body: email body (HTML-ready)
  - cta: call-to-action
  - send_day: recommended day to send (day 0, 1, 3, 5, etc.)
- notes: general tips for this sequence"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    content = response.choices[0].message.content
    store = _get_store()
    asset = store.create_content_asset(
        asset_type="email_sequence",
        title=f"{sequence_type.title()} Sequence - {domain}",
        content=content,
        domain=domain,
        metadata={"sequence_type": sequence_type, "audience": audience, "num_emails": num_emails},
    )

    return {"asset_id": asset.asset_id, "domain": domain, "sequence": content}


async def generate_landing_page(
    domain: str, offer: str, audience: str, cta: str = "Get Started"
) -> dict[str, Any]:
    """Generate landing page content."""
    client = _get_client()

    prompt = f"""Create landing page content:
- Domain: {domain}
- Offer: {offer}
- Target Audience: {audience}
- Primary CTA: {cta}

Return a JSON object with:
- headline: powerful headline
- subheadline: supporting copy
- hero_section: above-the-fold content
- benefits: array of benefit statements with icon suggestions
- social_proof: testimonial/trust elements suggestions
- faq: array of common Q&A
- cta_sections: array of CTA placements with text
- meta_title: SEO title
- meta_description: SEO description"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    content = response.choices[0].message.content
    store = _get_store()
    asset = store.create_content_asset(
        asset_type="landing_page",
        title=f"Landing Page: {offer} - {domain}",
        content=content,
        domain=domain,
        metadata={"offer": offer, "audience": audience, "cta": cta},
    )

    return {"asset_id": asset.asset_id, "domain": domain, "landing_page": content}


async def run(request: dict[str, Any]) -> dict[str, Any]:
    """Main entry point for the content creator agent."""
    action = request.get("action", "")
    domain = request.get("domain", "")

    if action == "website_copy":
        return await generate_website_copy(
            domain=domain,
            page_type=request.get("page_type", "homepage"),
            business_context=request.get("business_context", ""),
            tone=request.get("tone", "professional"),
        )
    elif action == "blog_post":
        return await generate_blog_post(
            domain=domain,
            topic=request.get("topic", ""),
            keywords=request.get("keywords", []),
            word_count=request.get("word_count", 800),
        )
    elif action == "email_sequence":
        return await generate_email_sequence(
            domain=domain,
            sequence_type=request.get("sequence_type", "welcome"),
            audience=request.get("audience", ""),
            num_emails=request.get("num_emails", 5),
        )
    elif action == "landing_page":
        return await generate_landing_page(
            domain=domain,
            offer=request.get("offer", ""),
            audience=request.get("audience", ""),
            cta=request.get("cta", "Get Started"),
        )
    else:
        return {"error": f"Unknown action: {action}"}
