"""
Glyph Map — Compression Language for Spatium Computationis
⌬ = compressed operational intelligence

Each glyph represents a compressed unit of meaning in the system.
"""

GLYPH_MAP: dict[str, dict] = {
    "⌬": {
        "name": "Nexus",
        "region": "core",
        "meaning": "compressed operational intelligence",
        "agent": "auctor_operis",
    },
    "✦": {
        "name": "Designium",
        "region": "regio_designii",
        "meaning": "designer intent",
        "agent": "interpres_designii",
    },
    "◈": {
        "name": "Mobilia",
        "region": "regio_mobilia",
        "meaning": "furniture object intelligence",
        "agent": "estimator_mobilia",
    },
    "⚒": {
        "name": "Laboris",
        "region": "regio_laboris",
        "meaning": "install labor",
        "agent": "estimator_laboris",
    },
    "⟁": {
        "name": "Campus",
        "region": "regio_campi",
        "meaning": "field condition",
        "agent": "inspector_campi",
    },
    "▣": {
        "name": "Documentum",
        "region": "regio_documentorum",
        "meaning": "official paperwork",
        "agent": "scriptor_documentorum",
    },
    "⇄": {
        "name": "Interpres",
        "region": "regio_contractus",
        "meaning": "translation between parties",
        "agent": "interpres_designii",
    },
    "◉": {
        "name": "Memoria",
        "region": "memory",
        "meaning": "project memory",
        "agent": "custos_memoriae",
    },
    "⚡": {
        "name": "Actio",
        "region": "core",
        "meaning": "generated action",
        "agent": None,
    },
    "↺": {
        "name": "Reductus",
        "region": "core",
        "meaning": "field feedback loop",
        "agent": None,
    },
    "≡": {
        "name": "Ordinatio",
        "region": "core",
        "meaning": "structured sorting / routing",
        "agent": None,
    },
    "◈$": {
        "name": "Pretium Mobilia",
        "region": "regio_mobilia",
        "meaning": "furniture pricing logic",
        "agent": "estimator_mobilia",
    },
    "⚒$": {
        "name": "Pretium Laboris",
        "region": "regio_laboris",
        "meaning": "labor pricing logic",
        "agent": "estimator_laboris",
    },
    "⟁✓": {
        "name": "Veritas Campi",
        "region": "regio_campi",
        "meaning": "field verification logic",
        "agent": "inspector_campi",
    },
    "▣✎": {
        "name": "Scriptura",
        "region": "regio_documentorum",
        "meaning": "document generation logic",
        "agent": "scriptor_documentorum",
    },
    "✦⇄⚒": {
        "name": "Design-to-Field",
        "region": "regio_contractus",
        "meaning": "designer intent converted into install instructions",
        "agent": "interpres_designii",
    },
}

# Region → primary glyph
REGION_GLYPHS: dict[str, str] = {
    "regio_designii": "✦",
    "regio_mobilia": "◈",
    "regio_laboris": "⚒",
    "regio_campi": "⟁",
    "regio_documentorum": "▣",
    "regio_contractus": "⇄",
    "memory": "◉",
    "core": "⌬",
}

# Agent → canonical glyph
AGENT_GLYPHS: dict[str, str] = {
    "auctor_operis": "⌬",
    "estimator_mobilia": "◈$",
    "estimator_laboris": "⚒$",
    "inspector_campi": "⟁✓",
    "scriptor_documentorum": "▣✎",
    "interpres_designii": "✦⇄⚒",
    "custos_memoriae": "◉",
}


def glyph_for_region(region: str) -> str:
    return REGION_GLYPHS.get(region, "⌬")


def glyph_for_agent(agent: str) -> str:
    return AGENT_GLYPHS.get(agent, "⌬")


def describe(glyph: str) -> str:
    entry = GLYPH_MAP.get(glyph)
    if not entry:
        return f"Unknown glyph: {glyph}"
    return f"{glyph} [{entry['name']}] — {entry['meaning']}"
