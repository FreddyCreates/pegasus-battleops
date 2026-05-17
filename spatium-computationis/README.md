# Spatium Computationis ⌬

> *The activated computing space where project information becomes action.*

**Latin name:** Spatium Computationis  
**Glyph:** ⌬  
**Meaning:** Compressed operational intelligence for furniture, interiors, and field installation.

---

## What This Is

Spatium Computationis is an AI-powered intelligence layer that sits between:

- Interior designers
- Furniture vendors & manufacturers
- Installation crews & contractors
- Project managers & estimators
- Field workers & warehouse teams

It receives information in any form — emails, PDFs, photos, voice notes, quotes, drawings — and transforms it into estimates, documents, instructions, and field-ready intelligence.

---

## Architecture

```
spatium-computationis/
├── main.py                    # FastAPI entrypoint
├── schemas.py                 # All Pydantic data models
├── requirements.txt
│
├── protocols/                 # The 5 intelligence protocols
│   ├── ingressus.py           # →⌬  Input normalization
│   ├── compressio.py          # ⌬   Compress to intelligence object
│   ├── ordinatio.py           # ≡   Route to correct agent
│   ├── actio.py               # ⚡  Execute the action
│   └── reductus.py            # ↺   Field feedback loop
│
├── agents/                    # The 7 AI agents
│   ├── auctor-operis/         # ⌬    Prime orchestrator
│   ├── estimator-mobilia/     # ◈$   Furniture pricing
│   ├── estimator-laboris/     # ⚒$   Labor estimating
│   ├── inspector-campi/       # ⟁✓  Field / punch list
│   ├── scriptor-documentorum/ # ▣✎  Document generation
│   ├── interpres-designii/    # ✦⇄⚒ Designer-to-field
│   └── custos-memoriae/       # ◉    Project memory (SQLite)
│
├── glyphs/
│   └── glyph_map.py           # Compression language definitions
│
├── estimating/
│   ├── furniture_pricing.py   # FF&E reference pricing tables
│   └── labor_pricing.py       # Labor rate / time tables
│
├── documents/
│   └── templates/             # Jinja2 document templates
│
└── field/
    ├── photo_intake.py        # Image → base64 for vision pipeline
    ├── issue_tracking.py      # Field issue queries
    └── memory.db              # SQLite project memory store
```

---

## Intelligence Pipeline

```
Any Input (email, photo, PDF, voice, quote...)
    ↓
→⌬ Ingressus       — normalize & extract structured data (GPT-4o)
    ↓
⌬  Compressio      — compress into glyph-tagged intelligence object
    ↓
≡  Ordinatio       — classify & route to the correct agent
    ↓
⚡ Actio           — execute: estimate, generate doc, punch list, etc.
    ↓
Output: Furniture Budget | Labor Bid | Install Packet | Document | Punch List
```

Field updates loop back via **↺ Reductus**, updating memory and triggering re-estimation automatically.

---

## Quick Start

### 1. Install dependencies

```bash
cd spatium-computationis
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
export OPENAI_API_KEY=sk-...
```

### 3. Start the server

```bash
uvicorn spatium_computationis.main:app --reload
```

API docs available at: http://localhost:8000/docs

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | System health + glyph |
| `POST` | `/ingest` | Full pipeline: any input → action result |
| `POST` | `/field-update` | Field feedback loop (Reductus) |
| `POST` | `/memory/recall` | Query project memory (Custos Memoriae) |
| `POST` | `/agents/estimate-furniture` | Direct furniture budget (◈$) |
| `POST` | `/agents/estimate-labor` | Direct labor bid (⚒$) |
| `POST` | `/agents/punch-list` | Direct punch list (⟁✓) |
| `POST` | `/agents/install-packet` | Direct install packet (✦⇄⚒) |

---

## Example: Submit a furniture quote email

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "email",
    "content": "Hi, attached is our quote for the 4th floor buildout. 12 task chairs at $450 each, 2 conference tables at $3,200 each, and 8 side chairs at $280 each. Lead time is 8-10 weeks. Please confirm.",
    "project_id": "proj-4thfloor-001",
    "submitted_by": "vendor@hermanmiller.com"
  }'
```

---

## Glyph Reference

| Glyph | Name | Meaning |
|-------|------|---------|
| ⌬ | Nexus | Compressed operational intelligence |
| ✦ | Designium | Designer intent |
| ◈ | Mobilia | Furniture object intelligence |
| ⚒ | Laboris | Install labor |
| ⟁ | Campus | Field condition |
| ▣ | Documentum | Official paperwork |
| ⇄ | Interpres | Translation between parties |
| ◉ | Memoria | Project memory |
| ⚡ | Actio | Generated action |
| ↺ | Reductus | Field feedback loop |
| ≡ | Ordinatio | Structured routing |
| ◈$ | Pretium Mobilia | Furniture pricing |
| ⚒$ | Pretium Laboris | Labor pricing |
| ⟁✓ | Veritas Campi | Field verification |
| ▣✎ | Scriptura | Document generation |
| ✦⇄⚒ | Design-to-Field | Designer intent → installer instructions |

---

*⌬ = compressed project intelligence.*
